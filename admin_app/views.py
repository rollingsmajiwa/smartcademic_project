
from datetime import time

from django.utils import timezone
from rest_framework import generics
from rest_framework.permissions import IsAdminUser

from .models import Classroom, StudentProfile, TeacherProfile
from .serializers import (
    ClassroomSerializer,
    StudentProfileSerializer,
    TeacherProfileSerializer,
    TeacherAttendanceSerializer,
    AssignmentPostSerializer,
    ExamPostSerializer,
    AssignmentSubmissionSerializer,
    ExamSubmissionSerializer,
)

from student_app.models import (
    Assignment_post,
    Exam_post,
    AssignmentSubmission,
    ExamSubmission,
)

from teachers_app.models import TeacherAttendance


# ==========================================
# CLASSROOM VIEWS
# ==========================================

class ClassroomListCreateView(generics.ListCreateAPIView):
    queryset = Classroom.objects.all()
    serializer_class = ClassroomSerializer
    permission_classes = [IsAdminUser]


class ClassroomDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Classroom.objects.all()
    serializer_class = ClassroomSerializer
    permission_classes = [IsAdminUser]


# ==========================================
# STUDENT PROFILE VIEWS
# ==========================================

class StudentListCreateView(generics.ListCreateAPIView):
    queryset = StudentProfile.objects.all()
    serializer_class = StudentProfileSerializer
    permission_classes = [IsAdminUser]


class StudentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = StudentProfile.objects.all()
    serializer_class = StudentProfileSerializer
    permission_classes = [IsAdminUser]


# ==========================================
# TEACHER PROFILE VIEWS
# ==========================================

class TeacherListCreateView(generics.ListCreateAPIView):
    queryset = TeacherProfile.objects.all()
    serializer_class = TeacherProfileSerializer
    permission_classes = [IsAdminUser]


class TeacherDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TeacherProfile.objects.all()
    serializer_class = TeacherProfileSerializer
    permission_classes = [IsAdminUser]


# ==========================================
# TEACHER ATTENDANCE VIEWS
# ==========================================

class AdminTeacherAttendanceListView(generics.ListAPIView):
    serializer_class = TeacherAttendanceSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):

        now = timezone.localtime()
        today = now.date()
        current_time = now.time()

        ABSENT_DEADLINE = time(16, 30)

        # Get all teachers
        all_teachers = TeacherProfile.objects.all()

        # Ensure every teacher has an attendance record for today
        for teacher in all_teachers:

            attendance, created = TeacherAttendance.objects.get_or_create(
                teacher=teacher,
                date=today,
                defaults={
                    'status': 'Pending'
                }
            )

            # Mark teachers absent after 4:30 PM
            # if they have not checked in
            if (
                current_time >= ABSENT_DEADLINE
                and not attendance.check_in_time
                and attendance.status != 'Absent'
            ):
                attendance.status = 'Absent'
                attendance.save(update_fields=['status'])

        # Return attendance history
        return TeacherAttendance.objects.all().order_by(
            '-date',
            '-check_in_time'
        )


# ==========================================
# ASSIGNMENTS POSTED BY TEACHERS
# ==========================================

class AdminAssignmentPostListView(generics.ListCreateAPIView):
    queryset = Assignment_post.objects.all()
    serializer_class = AssignmentPostSerializer
    permission_classes = [IsAdminUser]


# ==========================================
# EXAMS POSTED BY TEACHERS
# ==========================================

class AdminExamPostListView(generics.ListCreateAPIView):
    queryset = Exam_post.objects.all()
    serializer_class = ExamPostSerializer
    permission_classes = [IsAdminUser]


# ==========================================
# STUDENT ASSIGNMENT SUBMISSIONS
# ==========================================

class AdminAssignmentSubmissionListView(generics.ListAPIView):
    queryset = AssignmentSubmission.objects.all()
    serializer_class = AssignmentSubmissionSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):

        queryset = super().get_queryset()

        # Optional filtering:
        # /api/admin/submissions/assignments/?is_marked=false

        is_marked = self.request.query_params.get('is_marked')

        if is_marked is not None:
            marked_bool = is_marked.lower() == 'true'
            queryset = queryset.filter(is_marked=marked_bool)

        return queryset


# ==========================================
# STUDENT EXAM SUBMISSIONS
# ==========================================

class AdminExamSubmissionListView(generics.ListAPIView):
    queryset = ExamSubmission.objects.all()
    serializer_class = ExamSubmissionSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):

        queryset = super().get_queryset()

        # Optional filtering:
        # /api/admin/submissions/exams/?is_marked=true

        is_marked = self.request.query_params.get('is_marked')

        if is_marked is not None:
            marked_bool = is_marked.lower() == 'true'
            queryset = queryset.filter(is_marked=marked_bool)

        return queryset
