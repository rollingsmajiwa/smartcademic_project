from django.contrib import admin
from .models import Assignment, AssignmentSubmission, StudyMaterial

# Register your models here.
admin.site.register(Assignment)
admin.site.register(AssignmentSubmission)
admin.site.register(StudyMaterial)