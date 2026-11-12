from datetime import time
from rest_framework.decorators import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status, permissions, generics
from rest_framework.permissions import IsAuthenticated
from .models import Assignment_post, Exam_post, Teacher, TeacherAttendance, StudentMark, TeacherRevisionMaterial
from .serializers import (
    AssignmentSerializer, ExamPostSerializer, TeacherSerializer, 
    AssignmentGradeSerializer, ExamGradeSerializer, TeacherAttendanceSerializer, 
    StudentMarkSerializer, TeacherRevisionMaterialSerializer 
)
from admin_app.models import StudentProfile, TeacherProfile
from django.db.models import Avg
from student_app.models import AssignmentSubmission, ExamSubmission
from student_app.serializers import AssignmentSubmissionSerializer, ExamSubmissionSerializer

import math
from django.utils import timezone

import pandas as pd
from django.http import HttpResponse
from rest_framework.views import APIView



# API endpoint to list teachers
class TeacherListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        teachers = Teacher.objects.all()
        data = [{"id": t.id, "name": str(t)} for t in teachers]
        return Response(data)

# API for revision materials
class TeacherRevisionsView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def get(self, request):
        materials = TeacherRevisionMaterial.objects.all().order_by('-uploaded_at')
        serializer = TeacherRevisionMaterialSerializer(materials, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = TeacherRevisionMaterialSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
# Teachers overview API
class TeacherOverviewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            teacher_profile = Teacher.objects.get(user=request.user)
        except Teacher.DoesNotExist:
            if request.user.is_staff or request.user.is_superuser:
                assignments = Assignment_post.objects.all()
                exams = Exam_post.objects.all() if 'Exam_post' in globals() else Assignment_post.objects.none()
                assignment_subs = AssignmentSubmission.objects.filter(assignment__in=assignments)
                exam_subs = ExamSubmission.objects.filter(exam__in=exams) if 'ExamSubmission' in globals() else AssignmentSubmission.objects.none()
                
                pending_assignments = assignment_subs.filter(grade__isnull=True).count()
                pending_exams = exam_subs.filter(score__isnull=True).count() if 'ExamSubmission' in globals() else 0

                return Response({
                    "total_assignments_posted": assignments.count(),
                    "assignments_posted": assignments.count(),
                    "total_exams_created": exams.count(),
                    "exams_created": exams.count(),
                    "total_submissions_received": assignment_subs.count() + exam_subs.count(),
                    "submissions_received": assignment_subs.count() + exam_subs.count(),
                    "pending_grades": pending_assignments + pending_exams
                })
            else:
                teacher_profile = Teacher.objects.create(user=request.user)

        assignments = Assignment_post.objects.filter(teacher=teacher_profile)
        exams = Exam_post.objects.filter(teacher=teacher_profile) if 'Exam_post' in globals() else Assignment_post.objects.none()

        assignment_subs = AssignmentSubmission.objects.filter(assignment__in=assignments)
        exam_subs = ExamSubmission.objects.filter(exam__in=exams) if 'ExamSubmission' in globals() else AssignmentSubmission.objects.none()

        pending_assignments = assignment_subs.filter(grade__isnull=True).count()
        pending_exams = exam_subs.filter(score__isnull=True).count() if 'ExamSubmission' in globals() else 0

        data = {
            "total_assignments_posted": assignments.count(),
            "assignments_posted": assignments.count(),
            "total_exams_created": exams.count(),
            "exams_created": exams.count(),
            "total_submissions_received": assignment_subs.count() + exam_subs.count(),
            "submissions_received": assignment_subs.count() + exam_subs.count(),
            "pending_grades": pending_assignments + pending_exams
        }
        return Response(data)

class Teacher_assignments_view(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, *args, **kwargs):
        assignments = Assignment_post.objects.all()
        serializer = AssignmentSerializer(assignments, many=True)
        return Response(serializer.data)
    
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

# Teachers to view assignment submissions with full typed answers & student details
class TeacherAssignmentSubmissionView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        try:
            teacher = request.user.teacher_profile
            submissions = AssignmentSubmission.objects.filter(assignment__teacher=teacher)
            serializer = AssignmentGradeSerializer(submissions, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except AttributeError:
            return Response({"error": "This user has no teacher profile"}, status=status.HTTP_400_BAD_REQUEST)

# Teachers to view exam submissions with full typed answers & student details
class TeacherExamSubmissionView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        try:
            teacher = request.user.teacher_profile
            submissions = ExamSubmission.objects.filter(exam__teacher=teacher)
            serializer = ExamGradeSerializer(submissions, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except AttributeError:
            return Response({"error": "This user has no teacher profile"}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, *args, **kwargs):
        serializer = ExamSubmissionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(student=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# View for teachers to grade submitted assignments (saves grades & qualitative reviews)
class AssignmentGradeSubmissionView(generics.UpdateAPIView):
    queryset = AssignmentSubmission.objects.all()
    serializer_class = AssignmentGradeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save()

# View for teachers to grade submitted exams (saves grades & qualitative reviews)
class ExamGradeSubmissionView(generics.UpdateAPIView):
    queryset = ExamSubmission.objects.all()
    serializer_class = ExamGradeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save()

class Teacher_exams_view(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, *args, **kwargs):
        exams = Exam_post.objects.all()
        serializer = ExamPostSerializer(exams, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        try:
            teacher_profile = Teacher.objects.get(user=request.user)
        except Teacher.DoesNotExist:
            teacher_profile = Teacher.objects.create(user=request.user)

        serializer = ExamPostSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(teacher=teacher_profile)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Teacher profile view
class Teacher_profile_view(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, pk, *args, **kwargs):
        try:
            teacher = Teacher.objects.get(pk=pk)
        except Teacher.DoesNotExist:
            return Response({'error': 'Teacher profile not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = TeacherSerializer(teacher)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def put(self, request, pk, *args, **kwargs):
        try:
            teacher = Teacher.objects.get(pk=pk)
        except Teacher.DoesNotExist:
            return Response({'error': 'Teacher profile not found'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = TeacherSerializer(teacher, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ==========================================
# TEACHER GPS ATTENDANCE SYSTEM
# ==========================================

# School GPS coordinates
LAT_FENCE = -1.1701575
LON_FENCE = 36.82750325

# Allowed distance from school: 500 metres
RADIUS_METERS = 500

# Attendance cutoff
ON_TIME_CUTOFF = time(7, 0)


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two GPS coordinates
    using the Haversine formula.
    Returns distance in metres.
    """

    earth_radius = 6371000

    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return earth_radius * c


class GeoFenceAttendanceView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        # Get submitted information
        teacher_tsc_id = request.data.get('tsc_number')
        direction = request.data.get('direction', 'in').lower()

        user_lat = request.data.get('latitude')
        user_lon = request.data.get('longitude')

        # ==================================
        # VALIDATE INPUT
        # ==================================

        if not teacher_tsc_id:
            return Response(
                {"error": "Teacher TSC Number is required!"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if direction not in ['in', 'out']:
            return Response(
                {"error": "Direction must be either 'in' or 'out'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if user_lat is None or user_lon is None:
            return Response(
                {"error": "GPS coordinates are required!"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user_lat = float(user_lat)
            user_lon = float(user_lon)

            if not (
                math.isfinite(user_lat)
                and math.isfinite(user_lon)
                and -90 <= user_lat <= 90
                and -180 <= user_lon <= 180
            ):
                raise ValueError

        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid GPS coordinates."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ==================================
        # FIND TEACHER
        # ==================================

        try:
            teacher = TeacherProfile.objects.get(
                tsc_number=teacher_tsc_id
            )

        except TeacherProfile.DoesNotExist:
            return Response(
                {"error": "Teacher not found with this TSC Number!"},
                status=status.HTTP_404_NOT_FOUND
            )

        # ==================================
        # VERIFY SCHOOL LOCATION
        # ==================================

        distance = calculate_distance(
            user_lat,
            user_lon,
            LAT_FENCE,
            LON_FENCE
        )

        is_inside = distance <= RADIUS_METERS

        # ==================================
        # GET CURRENT DATE AND TIME
        # ==================================

        current_time = timezone.localtime()
        today = current_time.date()

        # ==================================
        # GET TODAY'S ATTENDANCE RECORD
        # ==================================

        attendance = TeacherAttendance.objects.filter(
            teacher=teacher,
            date=today
        ).first()

        # ==================================
        # HANDLE AUTOMATIC CLOCK-OUT
        # ==================================

        if not is_inside:

            if (
                attendance
                and attendance.check_in_time
                and not attendance.check_out_time
            ):

                attendance.check_out_time = current_time

                attendance.save(
                    update_fields=['check_out_time']
                )

                return Response({
                    "success": True,
                    "message": "You left the school compound. Automatically clocked OUT.",
                    "time": current_time,
                    "status": attendance.status
                }, status=status.HTTP_200_OK)

            return Response({
                "error": "You are outside the school compound.",
                "distance_metres": round(distance, 2)
            }, status=status.HTTP_400_BAD_REQUEST)

        # ==================================
        # CREATE TODAY'S ATTENDANCE RECORD
        # ==================================

        if attendance is None:

            attendance = TeacherAttendance.objects.create(
                teacher=teacher,
                date=today,
                status='Absent'
            )

        # ==================================
        # HANDLE CLOCK-IN
        # ==================================

        if direction == 'in':

            if attendance.check_in_time:

                return Response({
                    "error": "You have already clocked in today.",
                    "status": attendance.status
                }, status=status.HTTP_400_BAD_REQUEST)

            attendance.check_in_time = current_time

            # Before or exactly 7:00 AM = Present
            # After 7:00 AM = Late

            if current_time.time() > ON_TIME_CUTOFF:

                attendance.status = 'Late'

            else:

                attendance.status = 'Present'

            attendance.save(
                update_fields=[
                    'check_in_time',
                    'status'
                ]
            )

        # ==================================
        # HANDLE CLOCK-OUT
        # ==================================

        elif direction == 'out':

            if not attendance.check_in_time:

                return Response({
                    "error": "You must clock in before clocking out."
                }, status=status.HTTP_400_BAD_REQUEST)

            if attendance.check_out_time:

                return Response({
                    "error": "You have already clocked out today."
                }, status=status.HTTP_400_BAD_REQUEST)

            attendance.check_out_time = current_time

            attendance.save(
                update_fields=['check_out_time']
            )

        # ==================================
        # SUCCESS RESPONSE
        # ==================================

        return Response({

            "success": True,

            "message": (
                "Successfully clocked IN."
                if direction == 'in'
                else "Successfully clocked OUT."
            ),

            "teacher": str(teacher),

            "date": today,

            "time": current_time,

            "distance_metres": round(distance, 2),

            "status": attendance.status,

            "check_in_time": attendance.check_in_time,

            "check_out_time": attendance.check_out_time

        }, status=status.HTTP_200_OK)

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
            marks_qs = StudentMark.objects.filter(student=student, class_name=class_name, term=term, year=2026)
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
        entries = data.get('entries', [])
        
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


from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
def get_grade_level(score):
    if score is None:
        return "-"
    if score >= 90:
        return "EE"
    elif score >= 70:
        return "ME"
    elif score >= 40:
        return "AE"
    else:
        return "BE"

SUBJECT_SHORT = {
    'maths': 'Maths', 'kiswahili': 'Kiswahili', 'english': 'English',
    'pretechnical_studies': 'Pre-Tech', 'integrated_science': 'Int. Sci',
    'social_studies': 'Soc. Studies', 'cre': 'CRE', 'arts': 'Arts',
    'agriculture': 'Agric',
}


class ClassAnalysisView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    SUBJECTS = [
        'maths', 'kiswahili', 'english', 'pretechnical_studies',
        'integrated_science', 'social_studies', 'cre', 'arts', 'agriculture'
    ]

    def get(self, request, class_name, term):
        subjects = self.SUBJECTS
        marks_qs = StudentMark.objects.filter(class_name=class_name, term=term, year=2026)
        export = request.GET.get('export')

        if not marks_qs.exists():
            if export:
                return Response({"detail": "No marks saved for this class and term yet."},
                                status=status.HTTP_404_NOT_FOUND)
            # Not an error: the teacher just has not entered marks yet
            return Response({
                "class_name": class_name, "term": term, "year": 2026,
                "subject_columns": subjects,
                "student_performance_table": [],
                "subject_means": {}, "total_class_mean": 0.0,
            }, status=status.HTTP_200_OK)

        # Keyed by student id, so two students with the same name are not merged
        students_data = {}
        for record in marks_qs.select_related('student', 'student__user'):
            sid = record.student_id
            if sid not in students_data:
                name = record.student.user.get_full_name() or record.student.user.username
                students_data[sid] = {
                    "admission_number": record.student.admission_number,
                    "name": name,
                    "subjects": {sub: {"score": 0.0, "level": "BE"} for sub in subjects},
                    "total_marks": 0.0,
                }
            score = float(record.marks)
            students_data[sid]["subjects"][record.subject] = {
                "score": score, "level": get_grade_level(score),
            }
            students_data[sid]["total_marks"] += score

        student_list = sorted(students_data.values(), key=lambda x: x["total_marks"], reverse=True)
        for rank, student in enumerate(student_list, start=1):
            student["rank"] = rank

        subject_means = {}
        for sub in subjects:
            avg = marks_qs.filter(subject=sub).aggregate(Avg('marks'))['marks__avg']
            subject_means[sub] = round(float(avg), 2) if avg else 0.0

        # Total class mean = sum of every learner's total marks / number of learners
        total_class_mean = (
        round(sum(s["total_marks"] for s in student_list) / len(student_list), 2)
        if student_list else 0.0
        )

        if export == 'pdf':
            return self.export_to_pdf(student_list, subjects, subject_means,
                                      total_class_mean, class_name, term)

        return Response({
            "class_name": class_name, "term": term, "year": 2026,
            "subject_columns": subjects,
            "student_performance_table": student_list,
            "subject_means": subject_means,
            "total_class_mean": total_class_mean,
        }, status=status.HTTP_200_OK)

    def export_to_pdf(self, student_list, subjects, subject_means, total_class_mean, class_name, term):
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=landscape(A4),
            leftMargin=24, rightMargin=24, topMargin=24, bottomMargin=24,
        )
        styles = getSampleStyleSheet()
        elements = [
            Paragraph(f"Class Performance Report: {class_name}, {term} 2026", styles['Title']),
            Paragraph(f"Students: {len(student_list)} &nbsp;&nbsp; Class mean: {total_class_mean}", styles['Normal']),
            Spacer(1, 12),
        ]

        data = [['Rank', 'Adm No', 'Student'] + [SUBJECT_SHORT.get(s, s) for s in subjects] + ['Total']]
        for s in student_list:
            row = [s["rank"], s["admission_number"], s["name"]]
            for sub in subjects:
                d = s["subjects"][sub]
                row.append(f"{d['score']:g} {d['level']}")
            row.append(f"{s['total_marks']:g}")
            data.append(row)
        data.append(['', '', 'Subject mean'] + [f"{subject_means.get(sub, 0):g}" for sub in subjects] + [''])

        col_widths = [32, 55, 130] + [56] * len(subjects) + [50]
        table = Table(data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10002b')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (3, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#999999')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f5ecff')]),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e0c3fc')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("Levels: EE 90 and above, ME 70-89, AE 40-69, BE below 40.", styles['Normal']))

        doc.build(elements)

        filename = f"{class_name}_{term}_Class_Report.pdf".replace(' ', '_')
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
class ClassListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Resolve the Classroom model from StudentProfile.classroom so no import name is guessed
        Classroom = StudentProfile._meta.get_field('classroom').related_model
        data = [{"id": c.id, "name": c.name} for c in Classroom.objects.all().order_by('name')]
        return Response(data)

