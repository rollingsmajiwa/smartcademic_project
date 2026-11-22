from django.db import models
from django.contrib.auth.models import User
from teachers_app.models import Assignment_post, Exam_post


class StudyMaterial(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file = models.FileField()
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

    # AI draft fields (human-in-the-loop before teacher saves final grade/grade_description)
    ai_suggested_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    ai_feedback = models.TextField(blank=True, default="")
    ai_needs_manual_review = models.BooleanField(default=False)
    ai_marked_at = models.DateTimeField(null=True, blank=True)


class Exam(models.Model):
    title = models.CharField(max_length=255)
    duration_minutes = models.IntegerField()
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

    # AI draft fields (human-in-the-loop before teacher saves final score/grade_description)
    ai_suggested_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    ai_feedback = models.TextField(blank=True, default="")
    ai_needs_manual_review = models.BooleanField(default=False)
    ai_marked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Submission: {self.exam.title} by {self.student.username} ({self.status})"