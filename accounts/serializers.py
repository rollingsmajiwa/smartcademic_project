from rest_framework import serializers
from django.contrib.auth.models import User
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import UserProfile

# Public Sign-Up Serializer (Defaults to 'student')
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password')

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )
        UserProfile.objects.create(user=user, role='student')
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