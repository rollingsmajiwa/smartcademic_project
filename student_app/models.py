from django.db import models
from django.contrib.auth.models import User
from teachers_app.models import Assignment_post, Exam_post


# models to store study notes, assignments, assignment submissions, and exams.
class StudyMaterial(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file = models.FileField() # store files in data base
    uploaded_at = models.DateTimeField(auto_now_add=True)


class Assignment(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    file = models.FileField()
    deadline = models.DateTimeField()

class AssignmentSubmission(models.Model):
    assignment = models.ForeignKey(Assignment_post, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to='submissions/', blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    grade = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

class Exam(models.Model):
    title = models.CharField(max_length=255)
    duration_minutes = models.IntegerField() # for the React countdown timer
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

class ExamSubmission(models.Model):
    exam = models.ForeignKey(Exam_post, on_delete=models.CASCADE, related_name='exam_submissions')
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    answers_json = models.JSONField() # Stores student's answers
    file = models.FileField() # students can upload exams inform of files
    submitted_at = models.DateTimeField(auto_now_add=True)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    is_auto_submitted = models.BooleanField(default=False) # for countdown timers
    def __str__(self):
        status = "Auto-Submission" if self.is_auto_submitted else "Manual"
        return f"Submission: {self.exam.title} by {self.student.username} ({status})"
