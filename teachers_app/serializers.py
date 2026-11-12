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
    
    teacher_name = serializers.SerializerMethodField()
    surname = serializers.CharField(source='teacher.surname', read_only=True)
    first_name = serializers.CharField(source='teacher.user.first_name', read_only=True)
    tsc_number = serializers.CharField(source='teacher.tsc_number', read_only=True)

    
    teacher_id = serializers.IntegerField(source='teacher.id', read_only=True)
    timestamp = serializers.DateTimeField(source='check_in_time', read_only=True)
    clock_out = serializers.DateTimeField(source='check_out_time', read_only=True)

    class Meta:
        model = TeacherAttendance
        fields = '__all__'

    def get_teacher_name(self, obj):
        if not obj.teacher:
            return "Unknown Teacher"
        parts = [
            obj.teacher.user.first_name,
            obj.teacher.surname,
            obj.teacher.user.last_name,
        ]
        return " ".join(p for p in parts if p)

class StudentMarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentMark
        fields = '__all__'