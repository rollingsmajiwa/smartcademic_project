from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Classroom, StudentProfile, TeacherProfile
from student_app.models import (Assignment_post, 
    Exam_post, AssignmentSubmission, ExamSubmission
)
from teachers_app.models import TeacherAttendance

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']

class ClassroomSerializer(serializers.ModelSerializer):
    total_students = serializers.SerializerMethodField()

    class Meta:
        model = Classroom
        fields = '__all__'

    def get_total_students(self, obj):
        return obj.total_students()

class StudentProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    first_name = serializers.CharField(source='user.first_name', required=False, allow_blank=True)
    last_name = serializers.CharField(source='user.last_name', required=False, allow_blank=True)
    username = serializers.CharField(source='user.username', read_only=True)
    classroom_name = serializers.CharField(source='classroom.name', read_only=True, default='Unassigned')

    class Meta:
        model = StudentProfile
        fields = [
            'id', 
            'user', 
            'admission_number', 
            'first_name', 
            'surname', 
            'last_name', 
            'username', 
            'gender', 
            'date_admitted', 
            'classroom', 
            'classroom_name',
            'raw_password'
        ]

    def create(self, validated_data):
        user_data = validated_data.pop('user', {})
        first_name = user_data.get('first_name', '')
        last_name = user_data.get('last_name', '')
        
        username = first_name.strip() if first_name else 'student'
        
        password = validated_data.get('raw_password', 'password123')
        user = User.objects.create_user(
            username=username,
            first_name=first_name,
            last_name=last_name,
            password=password
        )
        student = StudentProfile.objects.create(user=user, **validated_data)
        return student

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        user = instance.user
        if 'first_name' in user_data:
            user.first_name = user_data['first_name']
            user.username = user_data['first_name']  
        if 'last_name' in user_data:
            user.last_name = user_data['last_name']
        
        raw_pwd = validated_data.get('raw_password')
        if raw_pwd:
            user.set_password(raw_pwd)
            user.save()
        else:
            user.save()

        return super().update(instance, validated_data)

class TeacherProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    first_name = serializers.CharField(source='user.first_name', required=False, allow_blank=True)
    last_name = serializers.CharField(source='user.last_name', required=False, allow_blank=True)
    email = serializers.CharField(source='user.email', required=False, allow_blank=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = TeacherProfile
        fields = [
            'id', 
            'user', 
            'tsc_number', 
            'first_name', 
            'surname', 
            'last_name', 
            'username', 
            'email', 
            'gender', 
            'date_joined', 
            'department', 
            'raw_password'
        ]

    def create(self, validated_data):
        user_info = validated_data.pop('user', {})
        first_name = user_info.get('first_name', '')
        last_name = user_info.get('last_name', '')
        email = user_info.get('email', '')
        
        if not email and 'email' in validated_data:
            email = validated_data.get('email', '')

        # Use email as username if provided, ensuring uniqueness for login lookups
        username = email if email else (first_name.strip() if first_name else 'teacher')
        
        password = validated_data.get('raw_password', 'password123')
        
        # Create core Django user with is_staff=True for OTP authentication
        user = User.objects.create_user(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=password,
            is_staff=True 
        )
        
        teacher = TeacherProfile.objects.create(user=user, **validated_data)
        return teacher

    def update(self, instance, validated_data):
        user_info = validated_data.pop('user', {})
        user = instance.user
        
        if 'first_name' in user_info:
            user.first_name = user_info['first_name']
        if 'last_name' in user_info:
            user.last_name = user_info['last_name']
        if 'email' in user_info:
            user.email = user_info['email']
            user.username = user_info['email'] # Keep username aligned with email
            
        user.is_staff = True # Enforce staff access status
        
        raw_pwd = validated_data.get('raw_password')
        if raw_pwd:
            user.set_password(raw_pwd)
            
        user.save()
        return super().update(instance, validated_data)

class TeacherAttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeacherAttendance
        fields = '__all__'

class AssignmentPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment_post
        fields = '__all__'

class ExamPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exam_post
        fields = '__all__'

class AssignmentSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssignmentSubmission
        fields = '__all__'

class ExamSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamSubmission
        fields = '__all__'