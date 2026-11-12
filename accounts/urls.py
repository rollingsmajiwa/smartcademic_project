from django.urls import path
from .views import (
    StudentRegisterView,
    StudentLoginView,
    SendUniversalOTPView,
    VerifyUniversalOTPView,
    AdminUserListCreateView,
    AdminUserDeleteView,
    GoogleAuthView,
    AdminInviteUserView,   
    SetPasswordView,        
    EmailPasswordLoginView  
)

urlpatterns = [
    # Student Auth Routes
    path('student/register/', StudentRegisterView.as_view(), name='student-register'),
    path('student/login/', StudentLoginView.as_view(), name='student-login'),

    # Staff / Admin OTP Routes
    path('staff/send-otp/', SendUniversalOTPView.as_view(), name='staff-send-otp'),
    path('staff/verify-otp/', VerifyUniversalOTPView.as_view(), name='staff-verify-otp'),

    # Standard Email & Password Login Route
    path('auth/login/password/', EmailPasswordLoginView.as_view(), name='email-password-login'),

    # Account Activation & Password Setup Route (From Email Link)
    path('auth/signup/', SetPasswordView.as_view(), name='signup'),

    # Admin Management & Invitation Routes
    path('admin/users/', AdminUserListCreateView.as_view(), name='admin-user-list-create'),
    path('admin/users/<int:id>/', AdminUserDeleteView.as_view(), name='admin-user-delete'),
    path('admin/invite/', AdminInviteUserView.as_view(), name='admin-invite'), # <--- Added

    # Google Auth Route
    path('auth/google/', GoogleAuthView.as_view(), name='google_auth'),
]