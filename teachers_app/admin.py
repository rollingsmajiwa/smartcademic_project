from django.contrib import admin
from .models import Teacher, Assignment_post, Exam_post


# Register your models here.
@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('id','name', 'teacher_id', 'department')

@admin.register(Assignment_post)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'teacher', 'deadline', 'description', 'file')

@admin.register(Exam_post)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'teacher', 'duration_mins','start_time', 'end_time', 'description', 'file')

