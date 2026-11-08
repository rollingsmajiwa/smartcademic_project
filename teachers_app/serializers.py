from rest_framework import serializers
from .models import Teacher, Assignment_post, Exam_post, TeacherAttendance, StudentMark, TeacherRevisionMaterial
from student_app.models import AssignmentSubmission, ExamSubmission

class TeacherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Teacher
        fields = '__all__'

class TeacherRevisionMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeacherRevisionMaterial
        fields = ['id', 'title', 'description', 'class_name','file', 'uploaded_at']

class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment_post
        fields = '__all__'
        read_only_fields = ['teacher']

class ExamPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exam_post
        fields = '__all__'
        read_only_fields = ['teacher']

# --- UPDATED: Full visibility for grading assignments ---
class AssignmentGradeSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    student_username = serializers.CharField(source='student.username', read_only=True)
    assignment_title = serializers.CharField(source='assignment.title', read_only=True)
    assignment_description = serializers.CharField(source='assignment.description', read_only=True)
    learning_area = serializers.CharField(source='assignment.course_name', default='General', read_only=True)

    class Meta:
        model = AssignmentSubmission
        fields = [
            'id', 'assignment', 'assignment_title', 'assignment_description', 
            'learning_area', 'student', 'student_name', 'student_username', 
            'answer_text', 'file', 'submitted_at', 'grade', 'grade_description'
        ]
        read_only_fields = ['student', 'assignment', 'submitted_at']

# --- UPDATED: Full visibility for grading exams ---
class ExamGradeSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    student_username = serializers.CharField(source='student.username', read_only=True)
    exam_title = serializers.CharField(source='exam.title', read_only=True)
    exam_description = serializers.CharField(source='exam.description', read_only=True)
    learning_area = serializers.CharField(source='exam.course_name', default='General', read_only=True)

    class Meta:
        model = ExamSubmission
        fields = [
            'id', 'exam', 'exam_title', 'exam_description', 'learning_area', 
            'student', 'student_name', 'student_username', 'answers_json', 
            'file', 'submitted_at', 'score', 'grade_description',
        ]
        read_only_fields = ['student', 'exam', 'submitted_at']

class TeacherAttendanceSerializer(serializers.ModelSerializer):
    """Serializer to view teacher attendance details and times"""
    teacher_name = serializers.CharField(source='teacher.name', read_only=True)

    class Meta:
        model = TeacherAttendance
        fields = ['id', 'teacher_name', 'date', 'check_in_time', 'check_out_time', 'status']

class StudentMarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentMark
        fields = ['id', 'student', 'subject', 'marks', 'term', 'year', 'class_name', 'teacher', 'updated_at']
        read_only_fields = ['teacher', 'updated_at', 'year']