from rest_framework.decorators import APIView
from rest_framework.response import Response
from django.db.models import Count
from django.utils import timezone
from rest_framework import status, generics, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from teachers_app.models import Exam_post, Assignment_post, TeacherRevisionMaterial
from teachers_app.serializers import ExamPostSerializer, AssignmentSerializer, TeacherRevisionMaterialSerializer
from .models import StudyMaterial, Assignment, AssignmentSubmission, Exam, ExamSubmission
from .serializers import (StudyMaterialSerializer, AssignmentSerializer, AssignmentSubmissionSerializer, 
    ExamSerializer, ExamSubmissionSerializer, StudentsAssignmentSubmissionSerializer, StudentExamSubmissionSerializer
)

# API view for Student Overview
class StudentOverviewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        total_assignments = Assignment_post.objects.count()
        total_exams = Exam_post.objects.count()
        total_tasks = total_assignments + total_exams

        completed_assignments = AssignmentSubmission.objects.filter(student=user).count()
        completed_exams = ExamSubmission.objects.filter(student=user).count()
        completed_tasks = completed_assignments + completed_exams

        urgent_deadlines = max(0, total_tasks - completed_tasks)

        data = {
            "student_name": user.get_full_name() or user.username,
            "term_info": "Term 1, 2026",
            "status_message": "Your profile is updated live from your academic records.",
            "mean_grade": "Active",
            "grade_description": "Calculated from submissions",
            "completed_tasks": completed_tasks,
            "total_tasks": total_tasks if total_tasks > 0 else 1,
            "completion_rate": f"{int((completed_tasks / total_tasks) * 100)}%" if total_tasks > 0 else "0%",
            "urgent_deadlines": urgent_deadlines,
            "urgent_notes": f"{urgent_deadlines} pending deadlines due soon",
            "performance_strands": []
        }

        return Response(data, status=status.HTTP_200_OK)

# API view Get revision Materials
class Study_material_list_view(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        materials = TeacherRevisionMaterial.objects.all().order_by('-uploaded_at')
        serializer = TeacherRevisionMaterialSerializer(materials, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

# API view to Get Assignments
class Assignment_list_view(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        assignments = Assignment_post.objects.all().order_by('deadline')
        serializer = AssignmentSerializer(assignments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# API view to Submit or Resubmit Assignment (Handles editing before deadline)
class Submit_assignment_view(APIView):  
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser] 

    def post(self, request, *args, **kwargs):
        student = request.user
        assignment_id = request.data.get('assignment')

        try:
            assignment = Assignment_post.objects.get(id=assignment_id)
        except Assignment_post.DoesNotExist:
            return Response({"detail": "Assignment not found."}, status=status.HTTP_404_NOT_FOUND)

        # Check deadline before allowing submission or resubmission
        if assignment.deadline and timezone.now() > assignment.deadline:
            return Response({"detail": "The deadline for this assignment has passed. Submission is closed."}, status=status.HTTP_400_BAD_REQUEST)

        # Use get_or_create to allow updates/resubmissions seamlessly without throwing duplicate errors
        submission, created = AssignmentSubmission.objects.get_or_create(
            assignment=assignment,
            student=student
        )

        answer_text = request.data.get('answer_text') or request.data.get('content')
        if answer_text is not None:
            submission.answer_text = answer_text

        if 'file' in request.FILES:
            submission.file = request.FILES['file']

        submission.submitted_at = timezone.now()
        submission.save()

        serializer = AssignmentSubmissionSerializer(submission)
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(serializer.data, status=status_code)


# API view to Submit or Update Exam
class Submit_exam_view(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser] 

    def post(self, request, *args, **kwargs):
        student = request.user
        exam_id = request.data.get('exam')

        try:
            exam = Exam_post.objects.get(id=exam_id)
        except Exam_post.DoesNotExist:
            return Response({"detail": "Exam not found."}, status=status.HTTP_404_NOT_FOUND)

        submission, created = ExamSubmission.objects.get_or_create(
            exam=exam,
            student=student
        )

        answer_text = request.data.get('answer_text') or request.data.get('content')
        if answer_text is not None:
            submission.answer_text = answer_text

        if 'answers_json' in request.data:
            submission.answers_json = request.data.get('answers_json')

        if 'file' in request.FILES:
            submission.file = request.FILES['file']

        submission.submitted_at = timezone.now()
        submission.save()

        serializer = ExamSubmissionSerializer(submission)
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(serializer.data, status=status_code)


# API view to Get Active Exams
class Exam_list_view(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        exams = Exam_post.objects.all()
        serializer = ExamPostSerializer(exams, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

# API view to get results of submitted assignment
class StudentsSubmittedAssignmentView(generics.ListAPIView):
    serializer_class = StudentsAssignmentSubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return AssignmentSubmission.objects.filter(student=self.request.user)

# API view to get results of submitted exam
class StudentsSubmittedExamView(generics.ListCreateAPIView):
    serializer_class = ExamSubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ExamSubmission.objects.filter(student=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(student=self.request.user)