from django.urls import path
from .views import Teacher_assignments_view, Teacher_exams_view, Teacher_profile_view, TeacherAssignmentSubmissionView, TeacherExamSubmissionView

urlpatterns = [
    path('assignment/', Teacher_assignments_view.as_view(), name="teacher-assignment"),
    path('exam/', Teacher_exams_view.as_view(), name="teacher-exam"),
    path('profile/<int:pk>/', Teacher_profile_view.as_view(), name="teacher-profile"),
    path('assignment-submissions/', TeacherAssignmentSubmissionView.as_view(), name='teacher-assignment-submissions'),
    path('exam-submissions/', TeacherExamSubmissionView.as_view(), name='teacher-exam-submissions')
]