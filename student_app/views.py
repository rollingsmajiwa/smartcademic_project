from rest_framework.decorators import APIView
from rest_framework.response import Response
from rest_framework import status, generics, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from teachers_app.models import Exam_post, Assignment_post
from teachers_app.serializers import ExamPostSerializer, AssignmentSerializer
from .models import StudyMaterial, Assignment, AssignmentSubmission, Exam, ExamSubmission
from .serializers import (StudyMaterialSerializer, AssignmentSerializer, AssignmentSubmissionSerializer, 
    ExamSerializer, ExamSubmissionSerializer, StudentsAssignmentSubmissionSerializer, StudentExamSubmissionSerializer
)


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