from rest_framework import serializers
from .models import Teacher, Assignment_post, Exam_post, TeacherAttendance, StudentMark
from student_app.models import AssignmentSubmission, ExamSubmission

class TeacherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Teacher
        fields = '__all__'


class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment_post
        fields = '__all__'

class ExamPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exam_post
        fields = '__all__'

class AssignmentGradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssignmentSubmission
        fields = ['grade']

class ExamGradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamSubmission
        fields = ['grade']
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