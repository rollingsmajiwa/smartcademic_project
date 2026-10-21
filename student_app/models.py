from django.db import models
from django.contrib.auth.models import User

# models to store study notes, assignments, assignment submissions, and exams.
class StudyMaterial(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='materials/')
    uploaded_at = models.DateTimeField(auto_now_add=True)


class Assignment(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    file = models.FileField(upload_to='assignments/', blank=True, null=True)
    deadline = models.DateTimeField()

class AssignmentSubmission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to='submissions/')
    submitted_at = models.DateTimeField(auto_now_add=True)
    grade = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

class Exam(models.Model):
    title = models.CharField(max_length=255)
    duration_minutes = models.IntegerField() # for the React countdown timer
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

class ExamSubmission(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='exam_submissions')
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    answers_json = models.JSONField() # Stores student's answers
    file = models.FileField(upload_to='exam_submission/', blank=True, null=True) # students can upload exams inform of files
    submitted_at = models.DateTimeField(auto_now_add=True)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
