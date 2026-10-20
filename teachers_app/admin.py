from django.contrib import admin
from .models import Teacher, Assignment_post, Exam_post

# Register your models here.
admin.site.register(Teacher)
admin.site.register(Assignment_post)
admin.site.register(Exam_post)