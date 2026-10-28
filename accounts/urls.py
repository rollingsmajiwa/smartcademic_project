from django.urls import path
from .views import RegisterView, AdminUserListCreateView, AdminUserDeleteView

urlpatterns = [
    path('api/register/', RegisterView.as_view(), name='register'),
    path('api/admin/users/', AdminUserListCreateView.as_view(), name='admin_user_list_create'),
    path('api/admin/users/<int:id>/', AdminUserDeleteView.as_view(), name='admin_user_delete'),
]