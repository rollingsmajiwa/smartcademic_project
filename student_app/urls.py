from django.urls import path
from .views import (study_materials_list, assignments_list, submit_assignment, submit_exam,
    exams_list
)

urlpatterns = [
    path('materials/', study_materials_list, name='learner-materials'),
    path('assignments/', assignments_list, name='learner-assignments'),
    path('assignments/submit/', submit_assignment, name='learner-submit-assignment'),
    path('exams/', exams_list, name='learner-exams'),
    path('exams/submit', submit_exam, name='learner-submit-exam')
]