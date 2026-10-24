from django.db import models
from django.contrib.auth.models import User
from admin_app.models import StudentProfile

# Create your models here.

class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    tsc_number = models.CharField(max_length=50, unique=True)
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

# model for manual marks entry
class StudentMark(models.Model):
    GRADE_CHOICES = [
        ('Grade 7', 'Grade 7'),
        ('Grade 8', 'Grade 8'),
        ('Grade 9', 'Grade 9'),
    ]

    TERM_CHOICES = [
        ('Term 1', 'Term 1'),
        ('Term 2', 'Term 2'),
        ('Term 3', 'Term 3'),
    ]

    SUBJECT_CHOICES = [
        ('maths', 'Maths'),
        ('kiswahili', 'Kiswahili'),
        ('english', 'English'),
        ('pretechnical_studies', 'Pre-Technical Studies'),
        ('integrated_science', 'Integrated Science'),
        ('social_studies', 'Social Studies'),
        ('cre', 'CRE'),
        ('arts', 'Arts'),
        ('agriculture', 'Agriculture'),
    ]

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='marks')
    subject = models.CharField(max_length=50, choices=SUBJECT_CHOICES)
    marks = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    term = models.CharField(max_length=20, choices=TERM_CHOICES, default='Term 1')
    year = models.IntegerField(default=2026)
    class_name = models.CharField(max_length=50, choices=GRADE_CHOICES)
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'subject', 'term', 'year', 'class_name')

    def __str__(self):
        return f"{self.student} - {self.subject}: {self.marks} ({self.class_name}, {self.term} 2026)"
