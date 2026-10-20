from rest_framework.decorators import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from .models import StudyMaterial, Assignment, AssignmentSubmission, Exam
from .serializers import (StudyMaterialSerializer, AssignmentSerializer, AssignmentSubmissionSerializer, 
    ExamSerializer, ExamSubmissionSerializer
)

# Get revision Materials
class Study_material_list_view(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        materials = StudyMaterial.objects.all().order_by('-uploaded_at')
        serializer = StudyMaterialSerializer(materials, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


#  Get Assignments
class assignment_list_view(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request, *args, **kwargs):
        assignments = Assignment.objects.all().order_by('deadline')
        serializer = AssignmentSerializer(assignments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# Submit Assignment
class submit_assignment_view(APIView):  
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser] # for file upload
    def post(self, request, *args, **kwargs):
        serializer = AssignmentSubmissionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(student=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# submit exam
class submit_exam_view(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser] # for file uploads
    def post(self, request, *args, **kwargs):
        serializer = ExamSubmissionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(student=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



# Get Active Exams
class exam_list_view(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        exams = Exam.objects.all()
        serializer = ExamSerializer(exams, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)