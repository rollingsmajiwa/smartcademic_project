from django.contrib import admin
from .models import Classroom, StudentProfile, TeacherProfile
from student_app.models import Assignment_post, Exam_post, AssignmentSubmission, ExamSubmission
from teachers_app.models import TeacherAttendance

@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'get_total_students')
    search_fields = ('name',)

    def get_total_students(self, obj):
        return obj.total_students()
    get_total_students.short_description = 'Total Students'


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('admission_number', 'get_full_name', 'classroom')
    search_fields = ('admission_number', 'user__first_name', 'user__last_name', 'user__username')
    list_filter = ('classroom',)

    def get_full_name(self, obj):
        return obj.user.get_full_name()
    get_full_name.short_description = 'Full Name'


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ('tsc_number', 'get_full_name', 'department')
    search_fields = ('tsc_number', 'user__first_name', 'user__last_name', 'department')
    list_filter = ('department',)

    def get_full_name(self, obj):
        return obj.user.get_full_name()
    get_full_name.short_description = 'Full Name'

@admin.register(TeacherAttendance)
class TeacherAttendanceAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'date', 'check_in_time', 'check_out_time', 'status')
    list_filter = ('date', 'status')

@admin.register(Assignment_post)
class AssignmentPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'teacher', 'classroom', 'due_date')
    list_filter = ('classroom', 'teacher')

@admin.register(Exam_post)
class ExamPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'teacher', 'classroom', 'exam_date')
    list_filter = ('classroom', 'teacher')

@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = ('student', 'assignment', 'is_marked', 'score', 'submitted_at')
    list_filter = ('is_marked', 'assignment__classroom')

@admin.register(ExamSubmission)
class ExamSubmissionAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam', 'is_marked', 'score', 'submitted_at')
    list_filter = ('is_marked', 'exam__classroom')