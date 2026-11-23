from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from admin_app.models import TeacherProfile, StudentProfile


class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    tsc_number = models.CharField(max_length=50, unique=True)
    department = models.CharField(max_length=100)
    name = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"Teacher: {self.user.get_full_name() or self.user.username}"


class TeacherRevisionMaterial(models.Model):
    title = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to='revisions/')
    class_name = models.CharField(max_length=50)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.class_name} - {self.title}"


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
    description = models.TextField(blank=True, null=True)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='exam_post')
    file = models.FileField(upload_to='exams/')
    duration_mins = models.IntegerField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Exam: {self.title} ({self.duration_mins} mins)"


class TeacherAttendance(models.Model):
    """Stores daily check-in, check-out time, week, month, and status for teachers"""
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField(default=timezone.now)
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default='Absent')
    week_number = models.IntegerField(null=True, blank=True)
    month = models.CharField(max_length=20, null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.date:
            self.week_number = self.date.isocalendar()[1]
            self.month = self.date.strftime('%B %Y')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.teacher.surname} - {self.date} [{self.status}] (Week {self.week_number})"


class StudentMark(models.Model):
    TERM_CHOICES = [
        ("Term 1", "Term 1"),
        ("Term 2", "Term 2"),
        ("Term 3", "Term 3"),
    ]

    EXAM_CHOICES = [
        ("Opener", "Opener"),
        ("Mid Term", "Mid Term"),
        ("End Term", "End Term"),
    ]

    SUBJECT_CHOICES = [
        ("maths", "Maths"),
        ("kiswahili", "Kiswahili"),
        ("english", "English"),
        ("pretechnical_studies", "Pre-Technical Studies"),
        ("integrated_science", "Integrated Science"),
        ("social_studies", "Social Studies"),
        ("cre", "CRE"),
        ("arts", "Arts"),
        ("agriculture", "Agriculture"),
    ]

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="marks")
    subject = models.CharField(max_length=50, choices=SUBJECT_CHOICES)
    marks = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    term = models.CharField(max_length=20, choices=TERM_CHOICES, default="Term 1")
    year = models.IntegerField(default=2026)
    exam_type = models.CharField(max_length=30, choices=EXAM_CHOICES, default="End Term", db_index=True)
    class_name = models.CharField(max_length=100)
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("student", "subject", "term", "year", "exam_type", "class_name")

    def __str__(self):
        return (
            f"{self.student} - {self.subject}: {self.marks} "
            f"({self.class_name}, {self.term} {self.year} - {self.exam_type})"
        )


class ReportFormTemplate(models.Model):
    """Stores a report form template; can use an uploaded file as the default template."""
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name='report_templates',
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='report_form_templates',
    )
    title = models.CharField(max_length=200, default="Custom Assessment Report")
    template_file = models.FileField(upload_to='report_templates/', blank=True, null=True)
    custom_html_template = models.TextField(blank=True, default="")
    use_default_template = models.BooleanField(default=False)
    is_default_template = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        label = "Default Uploaded" if self.is_default_template else ("Built-in Default" if self.use_default_template else "Custom")
        return f"{self.title} ({label})"