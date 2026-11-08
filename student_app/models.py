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
    answer_text = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to='submissions/', blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    grade = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    grade_description = models.TextField(blank=True, null=True)
    

class Exam(models.Model):
    title = models.CharField(max_length=255)
    duration_minutes = models.IntegerField() # for the React countdown timer
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

class ExamSubmission(models.Model):
    exam = models.ForeignKey(Exam_post, on_delete=models.CASCADE, related_name='exam_submissions')
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    answers_json = models.JSONField() 
    file = models.FileField(blank=True, null=True) 
    submitted_at = models.DateTimeField(auto_now_add=True)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    grade_description = models.TextField(blank=True, null=True)
    is_auto_submitted = models.BooleanField(default=False)
    status = models.CharField(max_length=50, default="Manual")

    def __str__(self):
        return f"Submission: {self.exam.title} by {self.student.username} ({self.status})"
