from django.urls import path
from .views import Teacher_assignments_view, Teacher_exams_view, Teacher_profile_view, TeacherAssignmentSubmissionView, TeacherExamSubmissionView, AssignmentGradeSubmissionView, ExamGradeSubmissionView, GeoFenceAttendanceView, ClassAnalysisView, ClassGradeTableView, BulkMarkSaveView, TeacherOverviewAPIView


urlpatterns = [
    path('assignment/', Teacher_assignments_view.as_view(), name="teacher-assignment"),
    path('exam/', Teacher_exams_view.as_view(), name="teacher-exam"),
    path('api/teachers/overview/', TeacherOverviewAPIView.as_view(), name='teacher-overview'),
    path('profile/<int:pk>/', Teacher_profile_view.as_view(), name="teacher-profile"),
    path('assignment-submissions/', TeacherAssignmentSubmissionView.as_view(), name='teacher-assignment-submissions'),
    path('exam-submissions/', TeacherExamSubmissionView.as_view(), name='teacher-exam-submissions'),
    path('submissions/<int:pk>/grade/',AssignmentGradeSubmissionView.as_view(), name='assignment_grade_submission' ),
    path('exams/submissions/<int:pk>/grade/', ExamGradeSubmissionView.as_view(), name='exam_grade_submission'),
    path('attendance/', GeoFenceAttendanceView.as_view(), name='geofence-attendance'),
    # Table data populated by Grade dropdown & Term dropdown
    path('grades/<str:class_name>/<str:term>/marks-table/', ClassGradeTableView.as_view(), name='class-marks-table'),
    
    # Bulk save marks from teacher's entry table
    path('grades/marks/bulk-save/', BulkMarkSaveView.as_view(), name='bulk-mark-save'),
    
    # Final analysis report with rankings, subject means, and class mean
    path('grades/analysis/<str:class_name>/<str:term>/', ClassAnalysisView.as_view(), name='class-analysis-report'),
]