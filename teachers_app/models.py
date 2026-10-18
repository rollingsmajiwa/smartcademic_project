from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    teacher_id = models.CharField(max_length=50, unique=True)
    department = models.CharField(max_length=100)
    def __str__(self):
        return f"Teacher:{self.user.get_full_name() or self.user.username}"
