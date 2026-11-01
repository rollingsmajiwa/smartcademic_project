from rest_framework.decorators import APIView
from rest_framework.response import Response
from django.db.models import Count
from django.utils import timezone
from rest_framework import status, generics, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from teachers_app.models import Exam_post, Assignment_post
from teachers_app.serializers import ExamPostSerializer, AssignmentSerializer
from .models import StudyMaterial, Assignment, AssignmentSubmission, Exam, ExamSubmission
from .serializers import (StudyMaterialSerializer, AssignmentSerializer, AssignmentSubmissionSerializer, 
    ExamSerializer, ExamSubmissionSerializer, StudentsAssignmentSubmissionSerializer, StudentExamSubmissionSerializer
)
# API view for Student Overwiew
from django.utils import timezone
from teachers_app.models import Assignment_post, Exam_post
from student_app.models import AssignmentSubmission, ExamSubmission
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class StudentOverviewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # 1. Dynamically count total posts from teacher models (No hardcoding)
        total_assignments = Assignment_post.objects.count()
        total_exams = Exam_post.objects.count()
        total_tasks = total_assignments + total_exams

        # 2. Dynamically count student's actual submissions
        completed_assignments = AssignmentSubmission.objects.filter(student=user).count()
        completed_exams = ExamSubmission.objects.filter(student=user).count()
        completed_tasks = completed_assignments + completed_exams

        # 3. Dynamically calculate pending deadlines (Total tasks minus completed tasks)
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
        materials = StudyMaterial.objects.all().order_by('-uploaded_at')
        serializer = StudyMaterialSerializer(materials, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


#  API view to Get Assignments
class Assignment_list_view(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request, *args, **kwargs):
        assignments = Assignment_post.objects.all().order_by('deadline')
        serializer = AssignmentSerializer(assignments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# API view to Submit Assignment
class Submit_assignment_view(APIView):  
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser] # for file upload
    def post(self, request, *args, **kwargs):
        serializer = AssignmentSubmissionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(student=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# API view to submit exam
class Submit_exam_view(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser] # essential for file uploads
    """Handles post exam request """
    def post(self, request, *args, **kwargs):
        serializer = ExamSubmissionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(student=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



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