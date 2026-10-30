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
class StudentOverviewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        now = timezone.now()

        # Calculate assignment completion 
        total_assignments = Assignment.objects.count()
        completed_submissions = AssignmentSubmission.objects.filter(student=user, is_submitted=True).count()
        completion_rate_val = (completed_submissions / total_assignments * 100) if total_assignments > 0 else 0

        # Calculate urgent deadlines due within the next 7 days
        urgent_count = Assignment.objects.filter(
            due_date__gte=now,
            due_date__lte=now + timezone.timedelta(days=7)
        ).exclude(submissions__student=user, submissions__is_submitted=True).count()

        #  dynamic JSON response
        data = {
            "student_name": user.get_full_name() or user.username,
            "term_info": "Term 1, 2026 • Current Week",
            "status_message": "Your profile metrics are updated live from your academic records.",
            "mean_grade": "Active",
            "grade_description": "Calculated from submissions",
            "completed_tasks": completed_submissions,
            "total_tasks": total_assignments,
            "completion_rate": f"{int(completion_rate_val)}%",
            "urgent_deadlines": urgent_count,
            "urgent_notes": f"{urgent_count} pending deadlines due soon",
            "attendance_rate": "Live Status",
            "attendance_details": "Metrics synced with database",
            "performance_strands": []
        }

        return Response(data)

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
class StudentsSubmittedExamView(generics.ListAPIView):
    serializer_class = ExamSubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ExamSubmission.objects.filter(student=self.request.user)