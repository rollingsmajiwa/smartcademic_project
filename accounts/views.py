"""
Authentication views for SmartAcademic.

Sections:
0. Roles and permissions
1. Shared helpers (responses, tokens, OTP, admission numbers, admin approval)
2. Teacher & admin login (email + OTP)
3. Student registration & login (admission number + password)
4. Admin invitations (single & bulk), account activation & admin reminders
5. Email + password login
6. Google OAuth
7. Admin user management
"""
import hashlib
import logging
import secrets
from typing import Optional

import resend
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.db import models, transaction
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

# Initialize Resend API key
resend.api_key = getattr(settings, "RESEND_API_KEY", "")
RESEND_FROM_EMAIL = getattr(
    settings, "RESEND_FROM_EMAIL", "SmartAcademic <onboarding@resend.dev>"
)


# =============================================================================
# 0. ROLES AND PERMISSIONS
# =============================================================================
ADMIN = "admin"
TEACHER = "teacher"
STUDENT = "student"

ALL_ROLES = frozenset({ADMIN, TEACHER, STUDENT})
STAFF_ROLES = frozenset({ADMIN, TEACHER})  # roles allowed through OTP / Google login
RESTRICTED_ROLES = frozenset({STUDENT, TEACHER})  # require admin update after activation

ADMIN_APPROVAL_REQUIRED_MSG = (
    "Your account is activated, but an administrator must review and update your "
    "profile before you can log in."
)


def get_user_role(user) -> Optional[str]:
    """Resolve a user's role. This is the only place roles are decided.

    Priority:
    1. Superuser                           -> admin
    2. UserProfile.role (a valid role)     -> that role   (source of truth)
    3. A TeacherProfile / StudentProfile   -> teacher / student
    4. is_staff, only when nothing else is known -> admin
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
    """Allow authenticated, active users whose *database* role is allowed."""

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
    """Issue a JWT pair with the role embedded."""
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


def attach_role_profiles(user, role, is_admin_approved: Optional[bool] = None):
    """Create the profile rows for a role and keep the staff flag consistent."""
    defaults = {"role": role}
    if is_admin_approved is not None:
        defaults["is_admin_approved"] = is_admin_approved

    profile, created = UserProfile.objects.get_or_create(user=user, defaults=defaults)
    updates = []
    if not created and profile.role != role:
        profile.role = role
        updates.append("role")
    if not created and is_admin_approved is not None and profile.is_admin_approved != is_admin_approved:
        profile.is_admin_approved = is_admin_approved
        updates.append("is_admin_approved")
    if updates:
        profile.save(update_fields=updates)

    if role == ADMIN:
        if not user.is_staff:
            user.is_staff = True
            user.save(update_fields=["is_staff"])
        return

    if user.is_staff and not user.is_superuser:
        user.is_staff = False
        user.save(update_fields=["is_staff"])

    if role == TEACHER:
        TeacherProfile.objects.get_or_create(user=user)
    elif role == STUDENT:
        StudentProfile.objects.get_or_create(
            user=user, defaults={"admission_number": generate_admission_number()}
        )


def has_admin_approval(user) -> bool:
    """Return True if the user does not require post-activation admin update,
    or if an administrator has already updated/approved their account."""
    role = get_user_role(user)
    if role not in RESTRICTED_ROLES:
        return True
    profile = UserProfile.objects.filter(user=user).only("is_admin_approved").first()
    return bool(profile.is_admin_approved) if profile is not None else True


def notify_admins_of_activation(user, role: str):
    """Send a reminder email via Resend to active admins when a student or teacher activates."""
    if not getattr(settings, "RESEND_API_KEY", ""):
        return

    admin_emails = list(
        User.objects.filter(is_active=True)
        .filter(models.Q(is_superuser=True) | models.Q(profile__role=ADMIN))
        .values_list("email", flat=True)
        .distinct()
    )
    admin_emails = [addr.strip() for addr in admin_emails if addr and addr.strip()]
    if not admin_emails:
        return

    dashboard_url = f"{getattr(settings, 'FRONTEND_URL', '').rstrip('/')}/dashboard/admin"
    try:
        resend.Emails.send(
            {
                "from": RESEND_FROM_EMAIL,
                "to": admin_emails,
                "subject": f"Action Required: Update Activated {role.title()} Account",
                "html": f"""
                    <div style="font-family: Arial, sans-serif; color: #10002b; padding: 20px;">
                        <h2 style="color: #10002b;">Account Activation Reminder</h2>
                        <p>
                            <b>{user.email or user.username}</b> has just set their password and activated their
                            <b>{role}</b> account on SmartAcademic.
                        </p>
                        <p>
                            Login is restricted until an administrator reviews and updates their record
                            in the Admin Dashboard.
                        </p>
                        <p style="margin-top: 16px;">
                            <a href="{dashboard_url}" style="background-color: #c77dff; color: #10002b; padding: 10px 20px; text-decoration: none; border-radius: 6px; display: inline-block; font-weight: bold;">
                                Open Admin Dashboard
                            </a>
                        </p>
                    </div>
                """,
            }
        )
    except Exception as mail_err:
        logger.warning("Failed to send admin activation reminder for %s: %s", user.email, mail_err)


def staff_session(user, message):
    """Shared tail of the OTP and Google flows: admin/teacher only."""
    if not user.is_active:
        return error("Account is inactive.", status.HTTP_403_FORBIDDEN)

    role = get_user_role(user)
    if role not in STAFF_ROLES:
        return error("Unauthorized account type.", status.HTTP_403_FORBIDDEN)

    if not has_admin_approval(user):
        return error(ADMIN_APPROVAL_REQUIRED_MSG, status.HTTP_403_FORBIDDEN)

    return Response({**build_tokens(user, role), "message": message})


class PublicAPIView(APIView):
    """Unauthenticated endpoint with per-scope throttling."""

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]


# ---- OTP helpers -----------------------------------------------------------
def _otp_key(kind: str, email: str) -> str:
    digest = hashlib.sha256(email.encode()).hexdigest()
    return f"otp:{kind}:{digest}"


def _otp_hash(email: str, code: str) -> str:
    return salted_hmac("accounts.otp", f"{email}:{code}").hexdigest()


def reserve_otp_slot(email: str) -> bool:
    return cache.add(_otp_key("cooldown", email), 1, OTP_RESEND_COOLDOWN_SECONDS)


def create_otp(email: str) -> str:
    code = f"{secrets.randbelow(1_000_000):06d}"
    cache.set(_otp_key("code", email), _otp_hash(email, code), OTP_TTL_SECONDS)
    cache.set(_otp_key("attempts", email), 0, OTP_TTL_SECONDS)
    return code


def check_otp(email: str, code) -> bool:
    code_key = _otp_key("code", email)
    attempts_key = _otp_key("attempts", email)

    stored = cache.get(code_key)
    if stored is None:
        return False

    try:
        attempts = cache.incr(attempts_key)
    except ValueError:
        cache.set(attempts_key, 1, OTP_TTL_SECONDS)
        attempts = 1

    if attempts > OTP_MAX_ATTEMPTS:
        cache.delete(code_key)
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

        if user and get_user_role(user) in STAFF_ROLES and has_admin_approval(user):
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
            UserProfile.objects.create(
                user=user, role=STUDENT, is_admin_approved=True
            )
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

        if not has_admin_approval(profile.user):
            return error(ADMIN_APPROVAL_REQUIRED_MSG, status.HTTP_403_FORBIDDEN)

        return Response({**build_tokens(profile.user, STUDENT), "message": "Login successful!"})


# =============================================================================
# 4. ADMIN INVITATIONS, ACCOUNT ACTIVATION & ADMIN REMINDERS
# =============================================================================
def _build_invite_html(role: str, link: str) -> str:
    return f"""
        <div style="font-family: Arial, sans-serif; color: #10002b; padding: 20px;">
            <h2 style="color: #10002b;">Welcome to SmartAcademic</h2>
            <p>You have been invited to join as a <b>{role}</b>.</p>
            <p>Click the button below to set your password and activate your account:</p>
            <a href="{link}" style="background-color: #c77dff; color: #10002b; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block; font-weight: bold; margin: 15px 0;">Activate Account</a>
            <p style="color: #666; font-size: 12px;">Or copy and paste this link into your browser:<br>{link}</p>
        </div>
    """


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

        needs_approval = role in RESTRICTED_ROLES

        try:
            with transaction.atomic():
                user = User.objects.create_user(username=email, email=email, is_active=False)
                attach_role_profiles(user, role, is_admin_approved=not needs_approval)

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            link = f"{getattr(settings, 'FRONTEND_URL', '').rstrip('/')}/signup?uid={uid}&token={token}"

            email_sent = False
            try:
                resend.Emails.send(
                    {
                        "from": RESEND_FROM_EMAIL,
                        "to": [email],
                        "subject": "Welcome to SmartAcademic - Set Your Password",
                        "html": _build_invite_html(role, link),
                    }
                )
                email_sent = True
            except Exception as mail_err:
                logger.warning("Resend HTTP API failed for %s: %s", email, mail_err)
                email_sent = False

        except Exception:
            logger.exception("Failed to create user %s", email)
            return error(
                "Could not create user invitation. Please try again.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "message": (
                    f"Invitation successfully emailed to {email}!"
                    if email_sent
                    else "User created, but email dispatch failed. Copy the link below."
                ),
                "email_sent": email_sent,
                "requires_admin_update_after_activation": needs_approval,
                "invite_link": link,
            },
            status=status.HTTP_201_CREATED,
        )


class AdminBulkInviteUserView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def post(self, request):
        raw_invites = request.data.get("invites")
        fallback_emails = request.data.get("emails")
        default_role = str(request.data.get("role") or TEACHER).strip().lower()

        items = []
        if isinstance(raw_invites, list):
            for entry in raw_invites:
                if isinstance(entry, dict):
                    items.append(
                        {
                            "email": normalize_email(entry.get("email")),
                            "role": str(entry.get("role") or default_role).strip().lower(),
                        }
                    )
                elif isinstance(entry, str):
                    items.append({"email": normalize_email(entry), "role": default_role})
        elif isinstance(fallback_emails, list):
            for addr in fallback_emails:
                items.append({"email": normalize_email(addr), "role": default_role})

        if not items:
            return error("Provide a non-empty list of invites or emails.")

        created_records = []
        skipped = []
        seen_emails = set()
        frontend_url = getattr(settings, "FRONTEND_URL", "").rstrip("/")

        for item in items:
            email = item["email"]
            role = item["role"]

            if not email:
                continue
            if email in seen_emails:
                skipped.append({"email": email, "reason": "Duplicate email in request."})
                continue
            seen_emails.add(email)

            if role not in ALL_ROLES:
                skipped.append(
                    {
                        "email": email,
                        "reason": f"Invalid role '{role}'. Must be one of: {', '.join(sorted(ALL_ROLES))}.",
                    }
                )
                continue

            if role == ADMIN and not request.user.is_superuser:
                skipped.append({"email": email, "reason": "Only superusers can invite admins."})
                continue

            if User.objects.filter(email__iexact=email).exists():
                skipped.append({"email": email, "reason": "User already exists."})
                continue

            needs_approval = role in RESTRICTED_ROLES

            try:
                with transaction.atomic():
                    user = User.objects.create_user(username=email, email=email, is_active=False)
                    attach_role_profiles(user, role, is_admin_approved=not needs_approval)

                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                link = f"{frontend_url}/signup?uid={uid}&token={token}"

                created_records.append(
                    {
                        "email": email,
                        "role": role,
                        "requires_admin_update_after_activation": needs_approval,
                        "invite_link": link,
                    }
                )
            except Exception as exc:
                logger.exception("Failed to create invited user %s", email)
                skipped.append({"email": email, "reason": str(exc) or "Could not create user record."})

        sent_count = 0
        failed_emails = []

        batch_payload = [
            {
                "from": RESEND_FROM_EMAIL,
                "to": [rec["email"]],
                "subject": "Welcome to SmartAcademic - Set Your Password",
                "html": _build_invite_html(rec["role"], rec["invite_link"]),
            }
            for rec in created_records
        ]

        for i in range(0, len(batch_payload), 100):
            chunk = batch_payload[i : i + 100]
            try:
                resend.Batch.send(chunk)
                sent_count += len(chunk)
            except Exception as batch_err:
                logger.warning("Resend Batch.send failed for chunk %s: %s", i // 100, batch_err)
                for msg in chunk:
                    failed_emails.append(msg["to"][0])

        return Response(
            {
                "message": f"Processed {len(created_records)} new invite(s); {sent_count} email(s) sent.",
                "created_count": len(created_records),
                "emails_sent": sent_count,
                "failed_email_deliveries": failed_emails,
                "skipped": skipped,
                "invites": created_records,
            },
            status=status.HTTP_201_CREATED if created_records else status.HTTP_200_OK,
        )


class SetPasswordView(PublicAPIView):
    throttle_scope = "password_set"

    def post(self, request):
        raw_uid = request.data.get("uid", "")
        raw_token = request.data.get("token", "")
        password = request.data.get("password")

        uid = str(raw_uid).strip()
        token = str(raw_token).strip()

        if not uid or not token or not password:
            return error("Missing activation details.")

        try:
            decoded_uid = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=decoded_uid)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            return error("Invalid activation link.")

        if not default_token_generator.check_token(user, token):
            return error("Token is invalid or has expired.")

        try:
            validate_password(password, user=user)
        except DjangoValidationError as exc:
            return password_error(exc)

        role = get_user_role(user) or STUDENT
        requires_admin_update = role in RESTRICTED_ROLES

        with transaction.atomic():
            user.set_password(password)
            user.is_active = True
            user.save(update_fields=["password", "is_active"])

            profile, _ = UserProfile.objects.get_or_create(user=user, defaults={"role": role})
            if requires_admin_update:
                profile.is_admin_approved = False
                profile.save(update_fields=["is_admin_approved"])

        if requires_admin_update:
            notify_admins_of_activation(user, role)
            return Response(
                {
                    "message": (
                        "Account activated! An administrator has been notified to review and "
                        "update your account before you can log in."
                    ),
                    "pending_admin_update": True,
                }
            )

        return Response(
            {
                "message": "Account activated successfully! You can now log in.",
                "pending_admin_update": False,
            }
        )


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

        if not has_admin_approval(user):
            return error(ADMIN_APPROVAL_REQUIRED_MSG, status.HTTP_403_FORBIDDEN)

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


class AdminUserDetailUpdateView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.select_related("profile").order_by("id")
    serializer_class = AdminUserManagementSerializer
    permission_classes = [IsAdminRole]
    lookup_field = "id"

    def perform_destroy(self, instance):
        if instance.pk == self.request.user.pk:
            raise PermissionDenied("You cannot delete your own account.")
        if instance.is_superuser and not self.request.user.is_superuser:
            raise PermissionDenied("Only superusers can delete a superuser.")
        instance.delete()


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