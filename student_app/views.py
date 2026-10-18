from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import StudyMaterial, Assignment, AssignmentSubmission, Exam
from .serializers import (StudyMaterialSerializer, AssignmentSerializer, AssignmentSubmissionSerializer, 
    ExamSerializer, ExamSubmissionSerializer
)

# Get revision Materials
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def study_materials_list(request):
    materials = StudyMaterial.objects.all().order_by('-uploaded_at')
    serializer = StudyMaterialSerializer(materials, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


#  Get Assignments
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def assignments_list(request):
    assignments = Assignment.objects.all().order_by('deadline')
    serializer = AssignmentSerializer(assignments, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


# Submit Assignment
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_assignment(request):
    serializer = AssignmentSubmissionSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(student=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# submit exam
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_exam(request):
    serializer = ExamSubmissionSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(student=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



# Get Active Exams
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def exams_list(request):
    exams = Exam.objects.all()
    serializer = ExamSerializer(exams, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)