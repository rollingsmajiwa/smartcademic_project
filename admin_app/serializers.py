from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Classroom, StudentProfile, TeacherProfile

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
    # Allows assigning user ID during updates
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='user', write_only=True
    )

    class Meta:
        model = StudentProfile
        fields = '__all__'

class TeacherProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='user', write_only=True
    )

    class Meta:
        model = TeacherProfile
        fields = '__all__'
