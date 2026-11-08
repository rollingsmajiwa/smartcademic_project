from django.urls import path
from .views import (
    Teacher_assignments_view, Teacher_exams_view, Teacher_profile_view, 
    TeacherAssignmentSubmissionView, TeacherExamSubmissionView, 
    AssignmentGradeSubmissionView, ExamGradeSubmissionView, 
    GeoFenceAttendanceView, ClassAnalysisView, ClassGradeTableView, 
    BulkMarkSaveView, TeacherOverviewAPIView, TeacherListView, TeacherRevisionsView
)

urlpatterns = [
    path('assignment/', Teacher_assignments_view.as_view(), name="teacher-assignment"),
    path('exam/', Teacher_exams_view.as_view(), name="teacher-exam"),
    path('overview/', TeacherOverviewAPIView.as_view(), name='teacher-overview'),
    path('profile/<int:pk>/', Teacher_profile_view.as_view(), name="teacher-profile"),
    
    # Submissions List & Detail Views for Teachers
    path('assignment-submissions/', TeacherAssignmentSubmissionView.as_view(), name='teacher-assignment-submissions'),
    path('assignment-submissions/<int:pk>/', TeacherAssignmentSubmissionView.as_view(), name='teacher-assignment-submission-detail'),
    
    path('exam-submissions/', TeacherExamSubmissionView.as_view(), name='teacher-exam-submissions'),
    path('exam-submissions/<int:pk>/', TeacherExamSubmissionView.as_view(), name='teacher-exam-submissions-detail'),
    
    # Grading & Review Save Endpoints (Updates marks & qualitative reviews)
    path('assignment-submissions/<int:pk>/grade/', AssignmentGradeSubmissionView.as_view(), name='assignment_grade_submission'),
    path('exam-submissions/<int:pk>/grade/', ExamGradeSubmissionView.as_view(), name='exam_grade_submission'),
    
    # Attendance & Revisions
    path('attendance/', GeoFenceAttendanceView.as_view(), name='geofence-attendance'),
    path('revisions/', TeacherRevisionsView.as_view(), name='teacher-revisions'),
    
    # Class Marks & Analysis Tables
    path('grades/<str:class_name>/<str:term>/marks-table/', ClassGradeTableView.as_view(), name='class-marks-table'),
    path('grades/marks/bulk-save/', BulkMarkSaveView.as_view(), name='bulk-mark-save'),
    path('grades/analysis/<str:class_name>/<str:term>/', ClassAnalysisView.as_view(), name='class-analysis-report'),
    
    path('list/', TeacherListView.as_view(), name='teacher-list'),
]