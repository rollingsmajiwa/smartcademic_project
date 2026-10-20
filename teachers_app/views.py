from rest_framework.decorators import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import Assignment_post, Exam_post, Teacher
from .serializers import AssignmentSerializer, ExamSerializer, TeacherSerializer


# Create your views here.

class Teacher_assignments_view(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes  = [MultiPartParser, FormParser]
    """ API view to retrieve already submitted assignment or to create new assignment """

    def get(self, request, *args, **kwargs):
        # List all assignments created by teachers
        assignments = Assignment_post.objects.all()
        serializer = AssignmentSerializer(assignments, many=True)
        return Response(serializer.data)
    
  
        # Teacher creates a new assignment (including uploading the file)
    def post(self, request, *args, **kwargs):
        serializer = AssignmentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class Teacher_exams_view(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    """API view to retrieve already submitted exams or to create new exams"""

    def get(self, request, *args, **kwargs):
    
        # List all timed exams created by teachers
        exams = Exam_post.objects.all()
        serializer = ExamSerializer(exams, many=True)
        return Response(serializer.data)
    
    
        # Teacher creates a new timed exam 
    def post(self, request, *args, **kwargs):
            serializer = ExamSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # teacher profile view
class Teacher_profile_view(APIView):
    permission_classes = [IsAuthenticated]
    """API view to retrieve existing teacher profile or to create a new profile"""
    def get(self, request, pk, *args, **kwargs):
        try:
            teacher = Teacher.objects.get(pk=pk)
        except Teacher.DoesNotExist:
            return Response({'error': 'Teacher profile not found'}, status=status.HTTP_404_NOT_FOUND)

    
        # Retrieve the specific teacher's profile
        serializer = TeacherSerializer(teacher)
        return Response(serializer.data, status=status.HTTP_200_OK)

    
    def put(self, request, pk, *args, **kwargs):
        try:
            teacher = Teacher.objects.get(pk=pk)
        except Teacher.DoesNotExist:
            return Response({'error': 'Teacher profile not found'}, status=status.HTTP_404_NOT_FOUND)
        
            

        # Update the teacher's profile
        serializer = TeacherSerializer(teacher, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)