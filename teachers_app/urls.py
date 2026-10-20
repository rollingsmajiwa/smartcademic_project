from django.urls import path
from .views import Teacher_assignments_view, Teacher_exams_view, Teacher_profile_view

urlpatterns = [
    path('assignment/', Teacher_assignments_view.as_view(), name="teacher-assignment"),
    path('exam/', Teacher_exams_view.as_view(), name="teacher-exam"),
    path('profile/<int:pk>/', Teacher_profile_view.as_view(), name="teacher-profile")
]