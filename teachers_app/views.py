from rest_framework.decorators import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status, permissions, generics
from rest_framework.permissions import IsAuthenticated
from .models import Assignment_post, Exam_post, Teacher, TeacherAttendance
from .serializers import AssignmentSerializer, ExamSerializer, TeacherSerializer, AssignmentGradeSerializer,ExamGradeSerializer, TeacherAttendanceSerializer 

from student_app.models import AssignmentSubmission, ExamSubmission
from student_app.serializers import AssignmentSubmissionSerializer, ExamSubmissionSerializer

import math
from django.utils import timezone


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

# teachers to view assginments submitted by students
class TeacherAssignmentSubmissionView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        # get loged-in teacher's profile
        try:
            teacher = request.user.teacher_profile
            submissions = AssignmentSubmission.objects.filter(assignment__teacher=teacher)
            serializer = AssignmentSubmissionSerializer(submissions, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except AttributeError:
            return Response({"error": "This user has no teacher profile"}, status=status.HTTP_400_BAD_REQUEST)

# teachers to view examss submitted by students
class TeacherExamSubmissionView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        # get loged-in teacher's profile
        try:
            teacher = request.user.teacher_profile
            submissions = ExamSubmission.objects.filter(exam__teacher=teacher)
            serializer = ExamSubmissionSerializer(submissions, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except AttributeError:
            return Response({"error": "This user has no teacher profile"}, status=status.HTTP_400_BAD_REQUEST)

# view for teachers to grade submitted assignment
class AssignmentGradeSubmissionView(generics.UpdateAPIView):
    queryset = AssignmentSubmission.objects.all()
    serializer_class = AssignmentGradeSerializer
    permission_classes = [permissions.IsAuthenticated]

    # only teachers can grade
    def perform_update(self, serializer):
        # save the updated grade
        serializer.save()

# view for teachers to grade submitted exams
class ExamGradeSubmissionView(generics.UpdateAPIView):
    queryset = ExamSubmission.objects.all()
    serializer_class = ExamGradeSerializer
    permission_classes = [permissions.IsAuthenticated]

    # only teachers can grade
    def perform_update(self, serializer):
        # save the updated grade
        serializer.save()

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

# School GPS Configuration, 
LAT_FENCE = -1.1701575
LON_FENCE = 36.82750325
RADIUS = 0.002  # Coordinate difference threshold

class GeoFenceAttendanceView(APIView):
    """
    API view to handle teacher check-in and check-out via Python geofencing logic.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        teacher_tsc_id = request.data.get('tsc_number')
        status_direction = request.data.get('direction')  # e.g., 'in' or 'out'
        user_lat = request.data.get('latitude')
        user_lon = request.data.get('longitude')

        # 1. Validate incoming data
        if not teacher_tsc_id or not status_direction:
            return Response(
                {"error": "Teacher ID and direction are required!"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if user_lat is None or user_lon is None:
            return Response(
                {"error": "GPS coordinates (latitude and longitude) are required!"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Find the teacher using their TSC Number
            teacher = Teacher.objects.get(tsc_number=teacher_tsc_id)
        except Teacher.DoesNotExist:
            return Response(
                {"error": "Teacher not found with this ID!"}, 
                status=status.HTTP_404_NOT_FOUND
            )

        # 2. Calculate coordinate difference (matching your simple JS logic)
        lat_distance = abs(float(user_lat) - LAT_FENCE)
        lon_distance = abs(float(user_lon) - LON_FENCE)

        is_inside = lat_distance < RADIUS and lon_distance < RADIUS

        if not is_inside:
            return Response(
                {"error": "You are outside the school compound."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Record attendance in database based on direction
        today = timezone.now().date()
        attendance, created = TeacherAttendance.objects.get_or_create(
            teacher=teacher, 
            date=today
        )

        current_time = timezone.localtime(timezone.now())

        if status_direction.lower() == 'in':
            if attendance.check_in_time:
                return Response({"message": "Already clocked in today."}, status=status.HTTP_400_BAD_REQUEST)
            attendance.check_in_time = current_time
            attendance.status = 'Present'
        elif status_direction.lower() == 'out':
            if attendance.check_out_time:
                return Response({"message": "Already clocked out today."}, status=status.HTTP_400_BAD_REQUEST)
            attendance.check_out_time = current_time
        
        attendance.save()

        return Response({
            "success": True,
            "message": f"Success! Clocked {status_direction}",
            "time": current_time
        }, status=status.HTTP_200_OK)