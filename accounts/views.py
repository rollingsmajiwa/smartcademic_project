from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.models import User
from .serializers import RegisterSerializer, AdminUserManagementSerializer
from .models import UserProfile

# Custom Permission to restrict views to Admin only
class IsAdminUserRole(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.role == 'admin'

# Public Registration Endpoint
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

# Admin Endpoint: List Users & Add User
class AdminUserListCreateView(generics.ListCreateAPIView):
    queryset = User.objects.all().select_related('profile')
    serializer_class = AdminUserManagementSerializer
    permission_classes = [IsAdminUserRole]

# Admin Endpoint: Delete User by ID
class AdminUserDeleteView(generics.DestroyAPIView):
    queryset = User.objects.all()
    serializer_class = AdminUserManagementSerializer
    permission_classes = [IsAdminUserRole]
    lookup_field = 'id'