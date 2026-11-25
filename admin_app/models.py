from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Classroom(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    teacher = models.ForeignKey(
        'admin_app.TeacherProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='classroom',
    )

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
    surname = models.CharField(max_length=100, blank=True, null=True)
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_profiles",
    )
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
    surname = models.CharField(max_length=100, blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)
    date_joined = models.DateField(default=timezone.now, blank=True, null=True)
    raw_password = models.CharField(max_length=128, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.user.first_name} {self.surname or ''} {self.user.last_name} - TSC: {self.tsc_number}"


class ParentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='parent_profile')
    phone_number = models.CharField(max_length=20, blank=True)
    children = models.ManyToManyField(
        'admin_app.StudentProfile',
        related_name='parents',
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} (Parent)"