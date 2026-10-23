from django.contrib import admin
from .models import Teacher, Assignment_post, Exam_post, TeacherAttendance


# Register your models here.
@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('id','name', 'tsc_number', 'department')

@admin.register(Assignment_post)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'teacher', 'deadline', 'description', 'file')

@admin.register(Exam_post)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'teacher', 'duration_mins','start_time', 'end_time', 'description', 'file')

@admin.register(TeacherAttendance)
class TeacherAttendanceAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'date', 'check_in_time', 'check_out_time', 'status')
    list_filter = ('date', 'status')
    search_fields = ('teacher__name', 'teacher__teacher_id')