from django.urls import path
from .views import (
    StudentRegisterView,
    StudentLoginView,
    SendUniversalOTPView,
    VerifyUniversalOTPView,
    AdminUserListCreateView,
    AdminUserDeleteView
)

urlpatterns = [
    # Student Auth Routes
    path('student/register/', StudentRegisterView.as_view(), name='student-register'),
    path('student/login/', StudentLoginView.as_view(), name='student-login'),

    # Staff / Admin OTP Routes
    path('staff/send-otp/', SendUniversalOTPView.as_view(), name='staff-send-otp'),
    path('staff/verify-otp/', VerifyUniversalOTPView.as_view(), name='staff-verify-otp'),

    # Admin Management Routes
    path('admin/users/', AdminUserListCreateView.as_view(), name='admin-user-list-create'),
    path('admin/users/<int:id>/', AdminUserDeleteView.as_view(), name='admin-user-delete'),
]