from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Create your models here.

class Classroom(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    teacher = models.ForeignKey('admin_app.TeacherProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='classroom')

    def __str__(self):
        return self.name

    def total_students(self):
        return self.student_profiles.count()


class StudentProfile(models.Model):
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")
    admission_number = models.CharField(max_length=50, unique=True)
    surname = models.CharField(max_length=100, blank=True, null=True)  # <-- Added surname field
    classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, null=True, blank=True, related_name="student_profiles")
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)
    date_admitted = models.DateField(default=timezone.now, blank=True, null=True)
    raw_password = models.CharField(max_length=128, blank=True, null=True)

    def __str__(self):
        return f"{self.user.first_name} {self.surname or ''} {self.user.last_name} ({self.admission_number})"


class TeacherProfile(models.Model):
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="admin_teacher_profile")
    tsc_number = models.CharField(max_length=50, unique=True)
    surname = models.CharField(max_length=100, blank=True, null=True)  # <-- Added surname
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)
    date_joined = models.DateField(default=timezone.now, blank=True, null=True)  # <-- Added date joined
    raw_password = models.CharField(max_length=128, blank=True, null=True)     # <-- Added raw password hint
    department = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.user.first_name} {self.surname or ''} {self.user.last_name} - TSC: {self.tsc_number}"