from rest_framework import serializers
from .models import Teacher, Assignment_post, Exam_post
from student_app.models import AssignmentSubmission, ExamSubmission

class TeacherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Teacher
        fields = '__all__'


class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment_post
        fields = '__all__'

class ExamSerializer(serializers.ModelSerializer):
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