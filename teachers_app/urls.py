from django.urls import path
from .views import teacher_assignments_view, teacher_exams_view, teacher_profile

urlpatterns = [
    path('teacher/assignment')
]