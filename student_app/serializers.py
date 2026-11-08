from rest_framework import serializers
from .models import StudyMaterial, Assignment_post, AssignmentSubmission, Exam, ExamSubmission

class StudyMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudyMaterial
        fields = '__all__'

class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment_post
        fields = '__all__'

class AssignmentSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssignmentSubmission
        fields = '__all__'
        read_only_fields = ['student', 'submitted_at', 'grade']

class ExamSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamSubmission
        fields = '__all__'
        read_only_fields = ['student', 'submitted_at', 'grade']

class ExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exam
        fields = '__all__'

# --- UPDATED: Pulls in assignment details, learning area, and answer text ---
class StudentsAssignmentSubmissionSerializer(serializers.ModelSerializer):
    assignment_title = serializers.CharField(source='assignment.title', read_only=True)
    assignment_description = serializers.CharField(source='assignment.description', read_only=True)
    learning_area = serializers.CharField(source='assignment.course_name', default='General', read_only=True)
    deadline = serializers.DateTimeField(source='assignment.deadline', read_only=True)
    assignment_file = serializers.FileField(source='assignment.file', read_only=True)

    class Meta:
        model = AssignmentSubmission
        fields = [
            'id', 'assignment', 'assignment_title', 'assignment_description', 
            'learning_area', 'deadline', 'assignment_file', 'answer_text', 
            'file', 'submitted_at', 'grade', 'grade_description'
        ]
        read_only_fields = ['grade', 'grade_description', 'submitted_at']

# --- UPDATED: Pulls in exam details, learning area, and typed answers ---
class StudentExamSubmissionSerializer(serializers.ModelSerializer):
    exam_title = serializers.CharField(source='exam.title', read_only=True)
    exam_description = serializers.CharField(source='exam.description', read_only=True)
    learning_area = serializers.CharField(source='exam.course_name', default='General', read_only=True)
    duration_mins = serializers.IntegerField(source='exam.duration_mins', read_only=True)

    class Meta:
        model = ExamSubmission
        fields = [
            'id', 'exam', 'exam_title', 'exam_description', 'learning_area', 
            'duration_mins', 'answers_json', 'answer_text', 'file', 'submitted_at', 'grade'
        ]
        read_only_fields = ['grade', 'submitted_at']