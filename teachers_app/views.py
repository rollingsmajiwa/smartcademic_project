from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from .models import Assignment_post, Exam_post, Teacher
from .serializers import AssignmentSerializer, ExamSerializer, TeacherSerializer


# Create your views here.

@api_view(['GET', 'POST'])
@parser_classes([MultiPartParser, FormParser])
def teacher_assignments_view(request):
    if request.method == 'GET':
        # List all assignments created by teachers
        assignments = Assignment_post.objects.all()
        serializer = AssignmentSerializer(assignments, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Teacher creates a new assignment (including uploading the file)
        serializer = AssignmentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'POST'])
@parser_classes([MultiPartParser, FormParser])
def teacher_exams_view(request):
    if request.method == 'GET':
        # List all timed exams created by teachers
        exams = Exam_post.objects.all()
        serializer = ExamSerializer(exams, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Teacher creates a new timed exam 
        serializer = ExamSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # teacher profile view
@api_view(['GET', 'PUT'])
def teacher_profile(request, pk):
    try:
        teacher = Teacher.objects.get(pk=pk)
    except Teacher.DoesNotExist:
        return Response({'error': 'Teacher profile not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        # Retrieve the specific teacher's profile
        serializer = TeacherSerializer(teacher)
        return Response(serializer.data)

    elif request.method == 'PUT':
        # Update the teacher's profile
        serializer = TeacherSerializer(teacher, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)