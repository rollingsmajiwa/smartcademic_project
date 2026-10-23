from django.contrib import admin
from .models import Classroom, StudentProfile, TeacherProfile

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