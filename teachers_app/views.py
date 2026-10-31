from rest_framework.decorators import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status, permissions, generics
from rest_framework.permissions import IsAuthenticated
from .models import Assignment_post, Exam_post, Teacher, TeacherAttendance, StudentMark
from .serializers import AssignmentSerializer, ExamPostSerializer, TeacherSerializer, AssignmentGradeSerializer,ExamGradeSerializer, TeacherAttendanceSerializer, StudentMarkSerializer 
from admin_app.models import StudentProfile
from django.db.models import Avg
from student_app.models import AssignmentSubmission, ExamSubmission
from student_app.serializers import AssignmentSubmissionSerializer, ExamSubmissionSerializer

import math
from django.utils import timezone


# Create your views here.
# API endpoint to list teachers
class TeacherListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        teachers = Teacher.objects.all()
        data = [{"id": t.id, "name": str(t)} for t in teachers]
        return Response(data)
    
# teachers overview api
class TeacherOverviewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        teacher = request.user
        
        # Filter content posted by this teacher
        assignments = Assignment_post.objects.filter(teacher=teacher)
        exams = Exam_post.objects.filter(teacher=teacher)
        
        # Get submissions tied to the teacher's assignments/exams
        assignment_submissions = AssignmentSubmission.objects.filter(assignment__in=assignments)
        exam_submissions = ExamSubmission.objects.filter(exam__in=exams)
        
        data = {
            "total_assignments_posted": assignments.count(),
            "total_exams_created": exams.count(),
            "total_submissions_received": assignment_submissions.count() + exam_submissions.count(),
            "pending_grades": assignment_submissions.filter(grade__isnull=True).count() + exam_submissions.filter(grade__isnull=True).count(),
        }
        return Response(data)

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
        try:
            teacher_profile = Teacher.objects.get(user=request.user)
        except Teacher.DoesNotExist:
            return Response({"error": "teacher profile not found"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = AssignmentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(teacher=teacher_profile)
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
        serializer = ExamPostSerializer(exams, many=True)
        return Response(serializer.data)
    
    
        # Teacher creates a new timed exam 
    def post(self, request, *args, **kwargs):
            serializer = ExamPostSerializer(data=request.data)
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

    # student mark view

class ClassGradeTableView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, class_name, term):
        students = StudentProfile.objects.filter(classroom__name=class_name)
        
        subjects = [
            {"key": "maths", "label": "Maths"},
            {"key": "kiswahili", "label": "Kiswahili"},
            {"key": "english", "label": "English"},
            {"key": "pretechnical_studies", "label": "Pre-Technical Studies"},
            {"key": "integrated_science", "label": "Integrated Science"},
            {"key": "social_studies", "label": "Social Studies"},
            {"key": "cre", "label": "CRE"},
            {"key": "arts", "label": "Arts"},
            {"key": "agriculture", "label": "Agriculture"}
        ]

        table_data = []
        for student in students:
            student_name = student.user.get_full_name() or student.user.username
            marks_qs = StudentMark.objects.filter(
                student=student, class_name=class_name, term=term, year=2026
            )
            marks_dict = {m.subject: float(m.marks) for m in marks_qs}

            student_row = {
                "student_id": student.id,
                "admission_number": student.admission_number,
                "student_name": student_name,
                "marks": {sub["key"]: marks_dict.get(sub["key"], 0.0) for sub in subjects}
            }
            table_data.append(student_row)

        return Response({
            "class_name": class_name,
            "term": term,
            "year": 2026,
            "subjects": subjects,
            "students_table": table_data
        }, status=status.HTTP_200_OK)


class BulkMarkSaveView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        data = request.data
        class_name = data.get('class_name')
        term = data.get('term')
        entries = data.get('entries', []) # List of {student_id, subject, marks}
        
        teacher = getattr(request.user, 'teacher_profile', None)

        for entry in entries:
            StudentMark.objects.update_or_create(
                student_id=entry.get('student_id'),
                subject=entry.get('subject'),
                class_name=class_name,
                term=term,
                year=2026,
                defaults={
                    'marks': entry.get('marks', 0.0), 
                    'teacher': teacher
                }
            )

        return Response({"detail": "Marks saved successfully!"}, status=status.HTTP_200_OK)


class ClassAnalysisView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, class_name, term):
        marks_qs = StudentMark.objects.filter(class_name=class_name, term=term, year=2026)
        
        if not marks_qs.exists():
            return Response({"detail": "No marks found for this grade and term."}, status=status.HTTP_404_NOT_FOUND)

        subjects = [
            'maths', 'kiswahili', 'english', 'pretechnical_studies', 
            'integrated_science', 'social_studies', 'cre', 'arts', 'agriculture'
        ]

        students_data = {}
        student_records = marks_qs.select_related('student', 'student__user')

        for record in student_records:
            student_name = record.student.user.get_full_name() or record.student.user.username
            if student_name not in students_data:
                students_data[student_name] = {
                    "admission_number": record.student.admission_number,
                    "name": student_name,
                    "subjects": {sub: 0.0 for sub in subjects},
                    "total_marks": 0.0
                }
            students_data[student_name]["subjects"][record.subject] = float(record.marks)
            students_data[student_name]["total_marks"] += float(record.marks)

        student_list = list(students_data.values())
        
        # Sort by total marks in descending order so rank 1 is highest scorer
        student_list = sorted(student_list, key=lambda x: x["total_marks"], reverse=True)

        # Assign rankings
        for rank, student in enumerate(student_list, start=1):
            student["rank"] = rank

        # Calculate Subject Means
        subject_means = {}
        for sub in subjects:
            avg_score = marks_qs.filter(subject=sub).aggregate(Avg('marks'))['marks__avg']
            subject_means[sub] = round(float(avg_score), 2) if avg_score else 0.0

        # Calculate Total Class Mean
        class_total_avg = marks_qs.aggregate(Avg('marks'))['marks__avg']
        total_class_mean = round(float(class_total_avg), 2) if class_total_avg else 0.0

        return Response({
            "class_name": class_name,
            "term": term,
            "year": 2026,
            "subject_columns": subjects,
            "student_performance_table": student_list,
            "subject_means": subject_means,
            "total_class_mean": total_class_mean
        }, status=status.HTTP_200_OK)