from django.urls import path
from .views import teacher_assignments_view, teacher_exams_view, teacher_profile_view

urlpatterns = [
    path('assignment/', teacher_assignments_view.as_view(), name="teacher-assignment"),
    path('exam/', teacher_exams_view.as_view(), name="teacher-exam"),
    path('profile/<int:pk>/', teacher_profile_view.as_view(), name="teacher-profile")
]