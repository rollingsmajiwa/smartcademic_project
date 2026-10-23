from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    teacher_id = models.CharField(max_length=50, unique=True)
    department = models.CharField(max_length=100)
    name = models.CharField(max_length=100, null=True, blank=True)
    def __str__(self):
        return f"Teacher:{self.user.get_full_name() or self.user.username}"


class Assignment_post(models.Model):
    title = models.CharField(max_length=250)
    description = models.TextField()
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='assignment_post')
    file = models.FileField(upload_to='assignment/')
    deadline = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Assignment: {self.title} by {self.teacher.user.username}"

class Exam_post(models.Model):
    title = models.CharField(max_length=250)
    description = models.TextField()
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='exam_post')
    file = models.FileField(upload_to='exams/')
    duration_mins = models.IntegerField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Exam: {self.title} ({self.duration_mins} mins)"




# model for teacher daily attendance
class TeacherAttendance(models.Model):
    """Stores daily check-in and check-out time and status for teachers"""
    teacher = models.ForeignKey('Teacher', on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField(auto_now_add=True)
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default='Absent')

    def __str__(self):
        return f"{self.teacher.name} - {self.date} ({self.status})"
