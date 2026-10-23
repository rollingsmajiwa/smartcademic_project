from rest_framework import generics
from rest_framework.permissions import IsAdminUser
from .models import Classroom, StudentProfile, TeacherProfile
from .serializers import (
    ClassroomSerializer, 
    StudentProfileSerializer, 
    TeacherProfileSerializer
)


# CLASSROOM VIEWS

class ClassroomListCreateView(generics.ListCreateAPIView):
    queryset = Classroom.objects.all()
    serializer_class = ClassroomSerializer
    permission_classes = [IsAdminUser]

class ClassroomDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Classroom.objects.all()
    serializer_class = ClassroomSerializer
    permission_classes = [IsAdminUser]



# STUDENT PROFILE VIEWS (Add, Edit, Delete, View)

class StudentListCreateView(generics.ListCreateAPIView):
    queryset = StudentProfile.objects.all()
    serializer_class = StudentProfileSerializer
    permission_classes = [IsAdminUser]

class StudentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = StudentProfile.objects.all()
    serializer_class = StudentProfileSerializer
    permission_classes = [IsAdminUser]



# TEACHER PROFILE VIEWS (Add, Edit, Delete, View)

class TeacherListCreateView(generics.ListCreateAPIView):
    queryset = TeacherProfile.objects.all()
    serializer_class = TeacherProfileSerializer
    permission_classes = [IsAdminUser]

class TeacherDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TeacherProfile.objects.all()
    serializer_class = TeacherProfileSerializer
    permission_classes = [IsAdminUser]
