from rest_framework import serializers
from django.contrib.auth.models import User
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import UserProfile
from admin_app.models import TeacherProfile, StudentProfile
import random

# Public Sign-Up Serializer (Defaults to 'student')
class RegisterSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(choices=[('student', 'Student'), ('teacher', 'Teacher')], default='student', write_only=True)

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'role']
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def create(self, validated_data):
        role = validated_data.pop('role', 'student')
        email = validated_data['email']
        
        # Use email as username for uniform password-less OTP flow
        user = User.objects.create_user(
            username=email,
            **validated_data
        )

        # 1. Store global role in UserProfile
        UserProfile.objects.create(user=user, role=role)

        # 2. Automatically generate the target profile type
        if role == 'teacher':
            TeacherProfile.objects.create(user=user)
        else:
            StudentProfile.objects.create(
                user=user,
                admission_number=f"STU-{random.randint(1000, 9999)}"
            )

        return user

# Custom JWT Serializer (Embeds role into JWT payload)
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Safely fetch role from UserProfile
        try:
            profile = UserProfile.objects.get(user=user)
            token['role'] = profile.role
        except UserProfile.DoesNotExist:
            token['role'] = 'student'  # Fallback only if no profile exists
            
        token['username'] = user.username
        return token

# Admin User Management Serializer
class AdminUserManagementSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source='profile.role', required=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'role')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        profile_data = validated_data.pop('profile', {})
        role = profile_data.get('role', 'student')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )
        UserProfile.objects.create(user=user, role=role)
        return user