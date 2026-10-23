from django.urls import path
from .views import (
    ClassroomListCreateView,
    ClassroomDetailView,
    StudentListCreateView,
    StudentDetailView,
    TeacherListCreateView,
    TeacherDetailView
)

urlpatterns = [
    # Classroom endpoints
    path('classrooms/', ClassroomListCreateView.as_view(), name='admin-classroom-list-create'),
    path('classrooms/<int:pk>/', ClassroomDetailView.as_view(), name='admin-classroom-detail'),

    # Student endpoints (Add, View, Edit, Delete)
    path('students/', StudentListCreateView.as_view(), name='admin-student-list-create'),
    path('students/<int:pk>/', StudentDetailView.as_view(), name='admin-student-detail'),

    # Teacher endpoints (Add, View, Edit, Delete)
    path('teachers/', TeacherListCreateView.as_view(), name='admin-teacher-list-create'),
    path('teachers/<int:pk>/', TeacherDetailView.as_view(), name='admin-teacher-detail'),
]