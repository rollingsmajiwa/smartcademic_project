from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Classroom(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    def total_students(self):
        return self.student_profiles.count()


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")
    admission_number = models.CharField(max_length=50, unique=True)
    classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, null=True, related_name="student_profiles")

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.admission_number})"


class TeacherProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="teacher_profile")
    tsc_number = models.CharField(max_length=50, unique=True)
    department = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.tsc_number})"
