from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.models import User
from .serializers import RegisterSerializer, AdminUserManagementSerializer
from .models import UserProfile
from admin_app.models import TeacherProfile, StudentProfile
import random
from django.core.mail import send_mail
from django.core.cache import cache
from rest_framework_simplejwt.tokens import RefreshToken


# ==========================================
# 1. TEACHER & ADMIN AUTHENTICATION (Email + OTP)
# ==========================================

class SendUniversalOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        if not email:
            return Response({'error': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check user or teacher profile properly using user__email
        user = User.objects.filter(email__iexact=email).first()
        is_admin = user and (user.is_superuser or user.is_staff)
        has_teacher_profile = TeacherProfile.objects.filter(user__email__iexact=email).exists() or (user and hasattr(user, 'teacherprofile'))

        if not is_admin and not has_teacher_profile:
            return Response({'error': 'No authorized staff or teacher account found with this email.'}, status=status.HTTP_404_NOT_FOUND)

        # 1. Generate 6-digit OTP
        otp_code = str(random.randint(100000, 999999))

        # 2. Store OTP in cache keyed by normalized email
        cache_key = f'otp_{email}'
        cache.set(cache_key, otp_code, timeout=300)
        
        # DEBUG: Print to terminal so you can verify cache storage instantly
        print(f"--- [SEND VIEW] Cached OTP for {cache_key}: {otp_code} ---")

        # 3. Send email
        try:
            send_mail(
                subject='Your Smart Academic Login Code',
                message=f'Your verification code is: {otp_code}',
                from_email=None,  # Uses DEFAULT_FROM_EMAIL in settings.py
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception as e:
            return Response({'error': f'Failed to send email: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'message': 'OTP sent successfully.'}, status=status.HTTP_200_OK)
class VerifyUniversalOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        otp_entered = request.data.get('otp')

        if not email or not otp_entered:
            return Response({'error': 'Both email and OTP code are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response({'error': 'Invalid request.'}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Match the exact email-based cache key format
        cache_key = f"otp_{email}"
        cached_otp = cache.get(cache_key)

        # DEBUG: Print to terminal to see what is being compared
        print(f"--- [VERIFY VIEW] Key: {cache_key} | Cached: {cached_otp} | Entered: {otp_entered} ---")

        if cached_otp and str(cached_otp).strip() == str(otp_entered).strip():
            # Clear the OTP so it cannot be reused
            cache.delete(cache_key)

            # 2. Check if a teacher profile exists safely via ForeignKey relationship
            is_teacher = TeacherProfile.objects.filter(user=user).exists()

            # 3. Accurately resolve role for admin vs teacher
            if user.is_superuser or user.is_staff or (hasattr(user, 'userprofile') and user.userprofile.role == 'admin'):
                role = 'admin'
            elif is_teacher:
                role = 'teacher'
            else:
                return Response({'error': 'Unauthorized account type.'}, status=status.HTTP_403_FORBIDDEN)

            # 4. Generate JWT tokens and attach the role
            refresh = RefreshToken.for_user(user)
            refresh['role'] = role

            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'role': role,
                'message': 'Authentication successful!'
            }, status=status.HTTP_200_OK)

        return Response({'error': 'Invalid or expired login code. Please try again.'}, status=status.HTTP_400_BAD_REQUEST)


# ==========================================
# 2. STUDENT REGISTRATION & LOGIN (Admission Number)
# ==========================================

class StudentRegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')

        if not first_name or not last_name:
            return Response({'error': 'First name and last name are required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Auto-generate unique school admission number
        admission_number = f"STU-{random.randint(10000, 99999)}"
        while StudentProfile.objects.filter(admission_number=admission_number).exists():
            admission_number = f"STU-{random.randint(10000, 99999)}"

        # Create user account without a password
        user = User.objects.create_user(
            username=admission_number,
            first_name=first_name,
            last_name=last_name
        )

        UserProfile.objects.create(user=user, role='student')
        StudentProfile.objects.create(user=user, admission_number=admission_number)

        refresh = RefreshToken.for_user(user)
        refresh['role'] = 'student'

        return Response({
            'admission_number': admission_number,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'role': 'student',
            'message': 'Registration successful!'
        }, status=status.HTTP_201_CREATED)


class StudentLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        admission_number = request.data.get('admission_number', '').strip().upper()

        if not admission_number:
            return Response({'error': 'Admission number is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            student = StudentProfile.objects.get(admission_number=admission_number)
            user = student.user
        except StudentProfile.DoesNotExist:
            return Response({'error': 'Invalid admission number.'}, status=status.HTTP_400_BAD_REQUEST)

        # Direct token generation (No password required)
        refresh = RefreshToken.for_user(user)
        refresh['role'] = 'student'

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'role': 'student',
            'message': 'Login successful!'
        }, status=status.HTTP_200_OK)



# 3. ADMIN USER MANAGEMENT & PERMISSIONS


class IsAdminUserRole(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'userprofile') and request.user.userprofile.role == 'admin'


class AdminUserListCreateView(generics.ListCreateAPIView):
    queryset = User.objects.all().select_related('userprofile')
    serializer_class = AdminUserManagementSerializer
    permission_classes = [IsAdminUserRole]


class AdminUserDeleteView(generics.DestroyAPIView):
    queryset = User.objects.all()
    serializer_class = AdminUserManagementSerializer
    permission_classes = [IsAdminUserRole]
    lookup_field = 'id'