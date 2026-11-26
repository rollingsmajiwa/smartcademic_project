from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import re
from django.db import models

# for parents
def normalize_phone_number(raw_phone: str | None) -> str:
    if not raw_phone:
        return ""
    digits = re.sub(r"\D", "", str(raw_phone))
    if not digits:
        return ""
    if digits.startswith("0") and len(digits) == 10:
        return "254" + digits[1:]
    if len(digits) == 9 and digits.startswith(("7", "1")):
        return "254" + digits
    return digits


class ParentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='parent_profile')
    phone_number = models.CharField(max_length=20, blank=True, db_index=True)
    children = models.ManyToManyField(
        'admin_app.StudentProfile',
        related_name='parents',
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def full_name(self) -> str:
        return self.user.get_full_name().strip() or self.user.username

    def save(self, *args, **kwargs):
        if self.phone_number:
            self.phone_number = normalize_phone_number(self.phone_number)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} (Parent)"


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


