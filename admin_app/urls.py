from django.urls import path
from .views import (
    ClassroomListCreateView,
    ClassroomDetailView,
    StudentListCreateView,
    StudentDetailView,
    TeacherListCreateView,
    TeacherDetailView,
    AdminTeacherAttendanceListView,
    AdminAssignmentPostListView,
    AdminExamPostListView,
    AdminAssignmentSubmissionListView,
    AdminExamSubmissionListView
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

    # Teacher Attendance tracking
    path('attendance/teachers/', AdminTeacherAttendanceListView.as_view(), name='admin-teacher-attendance'),

    # Assigned work view
    path('assignments/posts/', AdminAssignmentPostListView.as_view(), name='admin-assignment-posts'),
    path('exams/posts/', AdminExamPostListView.as_view(), name='admin-exam-posts'),

    # Student submissions (Marked / Unmarked)
    path('submissions/assignments/', AdminAssignmentSubmissionListView.as_view(), name='admin-assignment-submissions'),
    path('submissions/exams/', AdminExamSubmissionListView.as_view(), name='admin-exam-submissions')
]