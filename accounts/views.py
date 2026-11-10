"""
Authentication views for SmartAcademic.

Sections:
  0. Roles and permissions
  1. Shared helpers (responses, tokens, OTP, admission numbers)
  2. Teacher & admin login (email + OTP)
  3. Student registration & login (admission number + password)
  4. Admin invitations & account activation
  5. Email + password login
  6. Google OAuth
  7. Admin user management
"""
import hashlib
import logging
import secrets
from typing import Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.utils.crypto import constant_time_compare, salted_hmac
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from admin_app.models import StudentProfile, TeacherProfile

from .models import UserProfile
from .serializers import AdminUserManagementSerializer

User = get_user_model()
logger = logging.getLogger(__name__)


# =============================================================================
# 0. ROLES AND PERMISSIONS
# =============================================================================
ADMIN = "admin"
TEACHER = "teacher"
STUDENT = "student"

ALL_ROLES = frozenset({ADMIN, TEACHER, STUDENT})
STAFF_ROLES = frozenset({ADMIN, TEACHER})  # roles allowed through OTP / Google login


def get_user_role(user) -> Optional[str]:
    """Resolve a user's role. This is the only place roles are decided.

    Priority:
      1. Superuser                           -> admin
      2. UserProfile.role (a valid role)     -> that role   (source of truth)
      3. A TeacherProfile / StudentProfile   -> teacher / student
      4. is_staff, only when nothing else is known -> admin

    `is_staff` is deliberately last: it is a Django-admin-site flag, and
    accounts created by hand often have it set. If it outranked the profile
    role, teachers would be treated as admins.

    Direct queries are used instead of reverse attributes (user.teacherprofile)
    so this works whatever `related_name` the profile models use.
    """
    if user is None or not getattr(user, "pk", None):
        return None

    if user.is_superuser:
        return ADMIN

    profile = UserProfile.objects.filter(user=user).only("role").first()
    if profile is not None and profile.role in ALL_ROLES:
        return profile.role

    if TeacherProfile.objects.filter(user=user).exists():
        return TEACHER
    if StudentProfile.objects.filter(user=user).exists():
        return STUDENT

    if user.is_staff:
        return ADMIN

    return None


class HasRole(permissions.BasePermission):
    """Allow authenticated, active users whose *database* role is allowed.

    The role is read from the database on every request, not trusted from the
    JWT claim, so demoting a user takes effect immediately.
    """

    allowed_roles: frozenset = frozenset()

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and get_user_role(user) in self.allowed_roles
        )


class IsAdminRole(HasRole):
    allowed_roles = frozenset({ADMIN})


class IsTeacherRole(HasRole):
    allowed_roles = frozenset({TEACHER})


class IsStudentRole(HasRole):
    allowed_roles = frozenset({STUDENT})


class IsTeacherOrAdminRole(HasRole):
    allowed_roles = frozenset({ADMIN, TEACHER})


# Backwards-compatible alias for the old permission class name
IsAdminUserRole = IsAdminRole


# =============================================================================
# 1. SHARED HELPERS
# =============================================================================
OTP_TTL_SECONDS = 300
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_COOLDOWN_SECONDS = 60


def error(message, http_status=status.HTTP_400_BAD_REQUEST):
    return Response({"error": message}, status=http_status)


def password_error(exc: DjangoValidationError):
    return Response({"error": list(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)


def normalize_email(value) -> str:
    return str(value or "").strip().lower()


def build_tokens(user, role=None) -> dict:
    """Issue a JWT pair with the role embedded.

    simplejwt copies custom claims from the refresh token into the access
    token derived from it, so setting the claim once covers both.
    """
    role = role or get_user_role(user)
    refresh = RefreshToken.for_user(user)
    refresh["role"] = role
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "role": role,
    }


def generate_admission_number() -> str:
    for _ in range(20):
        candidate = f"STU-{secrets.randbelow(900_000) + 100_000}"
        if not StudentProfile.objects.filter(admission_number=candidate).exists():
            return candidate
    raise RuntimeError("Could not generate a unique admission number.")


def attach_role_profiles(user, role):
    """Create the profile rows for a role and keep the staff flag consistent."""
    UserProfile.objects.update_or_create(user=user, defaults={"role": role})

    if role == ADMIN:
        user.is_staff = True
        user.save(update_fields=["is_staff"])
        return

    # Only admins get Django-admin-site access.
    if user.is_staff and not user.is_superuser:
        user.is_staff = False
        user.save(update_fields=["is_staff"])

    if role == TEACHER:
        TeacherProfile.objects.get_or_create(user=user)
    elif role == STUDENT:
        StudentProfile.objects.get_or_create(
            user=user, defaults={"admission_number": generate_admission_number()}
        )


def staff_session(user, message):
    """Shared tail of the OTP and Google flows: admin/teacher only."""
    if not user.is_active:
        return error("Account is inactive.", status.HTTP_403_FORBIDDEN)

    role = get_user_role(user)
    if role not in STAFF_ROLES:
        return error("Unauthorized account type.", status.HTTP_403_FORBIDDEN)

    return Response({**build_tokens(user, role), "message": message})


class PublicAPIView(APIView):
    """Unauthenticated endpoint with per-scope throttling.

    `authentication_classes = []` stops a stale Authorization header from
    causing a 401 on endpoints that must be open. Set `throttle_scope` on
    subclasses; rates are configured in settings.
    """

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]


# ---- OTP helpers -----------------------------------------------------------
def _otp_key(kind: str, email: str) -> str:
    digest = hashlib.sha256(email.encode()).hexdigest()
    return f"otp:{kind}:{digest}"


def _otp_hash(email: str, code: str) -> str:
    # Stored hashed, so a cache dump does not reveal live codes.
    return salted_hmac("accounts.otp", f"{email}:{code}").hexdigest()


def reserve_otp_slot(email: str) -> bool:
    """Atomically claim the resend cooldown. False means 'too soon'."""
    return cache.add(_otp_key("cooldown", email), 1, OTP_RESEND_COOLDOWN_SECONDS)


def create_otp(email: str) -> str:
    code = f"{secrets.randbelow(1_000_000):06d}"  # cryptographically secure
    cache.set(_otp_key("code", email), _otp_hash(email, code), OTP_TTL_SECONDS)
    cache.set(_otp_key("attempts", email), 0, OTP_TTL_SECONDS)
    return code


def check_otp(email: str, code) -> bool:
    """Verify a code. Single use, with a cap on wrong guesses."""
    code_key = _otp_key("code", email)
    attempts_key = _otp_key("attempts", email)

    stored = cache.get(code_key)
    if stored is None:
        return False

    try:
        attempts = cache.incr(attempts_key)
    except ValueError:  # counter expired or missing
        cache.set(attempts_key, 1, OTP_TTL_SECONDS)
        attempts = 1

    if attempts > OTP_MAX_ATTEMPTS:
        cache.delete(code_key)  # burn the code; user must request a new one
        return False

    if constant_time_compare(stored, _otp_hash(email, str(code).strip())):
        cache.delete(code_key)
        cache.delete(attempts_key)
        return True
    return False


# =============================================================================
# 2. TEACHER & ADMIN AUTHENTICATION (Email + OTP)
# =============================================================================
class SendUniversalOTPView(PublicAPIView):
    throttle_scope = "otp_send"

    def post(self, request):
        email = normalize_email(request.data.get("email"))
        if not email:
            return error("Email is required.")

        if not reserve_otp_slot(email):
            return error(
                "Please wait a minute before requesting another code.",
                status.HTTP_429_TOO_MANY_REQUESTS,
            )

        user = User.objects.filter(email__iexact=email, is_active=True).first()

        # Only eligible accounts receive a code, but the response is identical
        # either way so the endpoint cannot be used to discover accounts.
        if user and get_user_role(user) in STAFF_ROLES:
            code = create_otp(email)
            try:
                send_mail(
                    subject="Your Smart Academic Login Code",
                    message=f"Your verification code is: {code}\n\nIt expires in 5 minutes.",
                    from_email=None,
                    recipient_list=[email],
                    fail_silently=False,
                )
            except Exception:
                logger.exception("Failed to send OTP email")
                return error(
                    "Could not send the verification email. Please try again later.",
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        return Response(
            {"message": "If an account exists for this email, a code has been sent."}
        )


class VerifyUniversalOTPView(PublicAPIView):
    throttle_scope = "otp_verify"

    def post(self, request):
        email = normalize_email(request.data.get("email"))
        otp = request.data.get("otp")

        if not email or not otp:
            return error("Both email and OTP code are required.")

        invalid = "Invalid or expired login code. Please try again."

        if not check_otp(email, otp):
            return error(invalid)

        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            return error(invalid)

        return staff_session(user, "Authentication successful!")


# =============================================================================
# 3. STUDENT REGISTRATION & LOGIN (Admission number + password)
# =============================================================================
class StudentRegisterView(PublicAPIView):
    throttle_scope = "register"

    def post(self, request):
        first_name = str(request.data.get("first_name") or "").strip()
        last_name = str(request.data.get("last_name") or "").strip()
        password = request.data.get("password") or ""

        if not first_name or not last_name:
            return error("First name and last name are required.")
        if not password:
            return error("A password is required.")

        try:
            validate_password(password)
        except DjangoValidationError as exc:
            return password_error(exc)

        with transaction.atomic():
            admission_number = generate_admission_number()
            user = User.objects.create_user(
                username=admission_number,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
            UserProfile.objects.create(user=user, role=STUDENT)
            StudentProfile.objects.create(user=user, admission_number=admission_number)

        return Response(
            {
                "admission_number": admission_number,
                **build_tokens(user, STUDENT),
                "message": "Registration successful!",
            },
            status=status.HTTP_201_CREATED,
        )


class StudentLoginView(PublicAPIView):
    throttle_scope = "login"

    def post(self, request):
        admission_number = str(request.data.get("admission_number") or "").strip().upper()
        password = request.data.get("password") or ""

        if not admission_number or not password:
            return error("Admission number and password are required.")

        profile = (
            StudentProfile.objects.select_related("user")
            .filter(admission_number=admission_number)
            .first()
        )
        if profile is None or not profile.user.check_password(password):
            return error("Invalid admission number or password.", status.HTTP_401_UNAUTHORIZED)

        if not profile.user.is_active:
            return error("Account is inactive.", status.HTTP_403_FORBIDDEN)

        return Response({**build_tokens(profile.user, STUDENT), "message": "Login successful!"})


# =============================================================================
# 4. ADMIN INVITATION & ACCOUNT ACTIVATION (Set password)
# =============================================================================
class AdminInviteUserView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def post(self, request):
        email = normalize_email(request.data.get("email"))
        role = str(request.data.get("role") or TEACHER).strip().lower()

        if not email:
            return error("Email is required.")
        if role not in ALL_ROLES:
            return error(f"Role must be one of: {', '.join(sorted(ALL_ROLES))}.")
        if role == ADMIN and not request.user.is_superuser:
            return error("Only superusers can invite admins.", status.HTTP_403_FORBIDDEN)
        if User.objects.filter(email__iexact=email).exists():
            return error("A user with this email already exists.")

        try:
            # If the email fails, the whole transaction rolls back, so no
            # orphaned inactive account is left behind.
            with transaction.atomic():
                user = User.objects.create_user(username=email, email=email, is_active=False)
                attach_role_profiles(user, role)

                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                link = f"{settings.FRONTEND_URL}/set-password?uid={uid}&token={token}"

                send_mail(
                    subject="Welcome to SmartAcademic - Set Your Password",
                    message=(
                        f"You have been invited as a {role}. "
                        f"Click the link below to set your password and activate your account:\n\n{link}"
                    ),
                    from_email=None,
                    recipient_list=[email],
                    fail_silently=False,
                )
        except Exception:
            logger.exception("Failed to create/invite user %s", email)
            return error(
                "Could not send the invitation. Please try again.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"message": f"Invitation successfully sent to {email}."},
            status=status.HTTP_201_CREATED,
        )


class SetPasswordView(PublicAPIView):
    throttle_scope = "password_set"

    def post(self, request):
        uid = request.data.get("uid")
        token = request.data.get("token")
        password = request.data.get("password")

        if not uid or not token or not password:
            return error("Missing activation details.")

        try:
            user = User.objects.get(pk=force_str(urlsafe_base64_decode(uid)))
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            return error("Invalid activation link.")

        if not default_token_generator.check_token(user, token):
            return error("Token is invalid or has expired.")

        try:
            validate_password(password, user=user)
        except DjangoValidationError as exc:
            return password_error(exc)

        # Identity fields (email/username) are deliberately NOT changeable here.
        # Changing the password also invalidates the token, making it single-use.
        user.set_password(password)
        user.is_active = True
        user.save(update_fields=["password", "is_active"])

        return Response({"message": "Account activated successfully! You can now log in."})


# =============================================================================
# 5. EMAIL & PASSWORD LOGIN
# =============================================================================
class EmailPasswordLoginView(PublicAPIView):
    throttle_scope = "login"

    def post(self, request):
        email = normalize_email(request.data.get("email"))
        password = request.data.get("password") or ""

        if not email or not password:
            return error("Email and password are required.")

        user = User.objects.filter(email__iexact=email).first()
        if user is None or not user.check_password(password):
            return error("Invalid email or password.", status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return error(
                "Account is inactive. Activate your account using your email link.",
                status.HTTP_403_FORBIDDEN,
            )

        role = get_user_role(user)
        if role is None:
            return error("This account has no role assigned.", status.HTTP_403_FORBIDDEN)

        return Response({**build_tokens(user, role), "message": "Login successful!"})


# =============================================================================
# 6. GOOGLE OAUTH
# =============================================================================
class GoogleAuthView(PublicAPIView):
    throttle_scope = "login"

    def post(self, request):
        token = request.data.get("token")
        if not token:
            return error("Google token is required.")

        try:
            idinfo = id_token.verify_oauth2_token(
                token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
            )
        except ValueError:
            return error("Invalid Google token.")

        email = normalize_email(idinfo.get("email"))
        if not email or not idinfo.get("email_verified"):
            return error("Your Google account does not have a verified email.")

        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            return error(
                "No authorized account found for this Google email.",
                status.HTTP_403_FORBIDDEN,
            )

        return staff_session(user, "Google authentication successful!")


# =============================================================================
# 7. ADMIN USER MANAGEMENT
# =============================================================================
class AdminUserListCreateView(generics.ListCreateAPIView):
    queryset = User.objects.select_related("profile").order_by("id")
    serializer_class = AdminUserManagementSerializer
    permission_classes = [IsAdminRole]


class AdminUserDeleteView(generics.DestroyAPIView):
    queryset = User.objects.all()
    permission_classes = [IsAdminRole]
    lookup_field = "id"

    def perform_destroy(self, instance):
        if instance.pk == self.request.user.pk:
            raise PermissionDenied("You cannot delete your own account.")
        if instance.is_superuser and not self.request.user.is_superuser:
            raise PermissionDenied("Only superusers can delete a superuser.")
        instance.delete()