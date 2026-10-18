from django.urls import path
from .views import (study_materials_list, assignments_list, submit_assignment, submit_exam,
    exams_list
)

urlpatterns = [
    path('learners/materials/', study_materials_list, name='learner-materials'),
    path('learners/assignments/', assignments_list, name='learner-assignments'),
    path('learners/assignments/submit/', submit_assignment, name='learner-submit-assignment'),
    path('learners/exams/', exams_list, name='learner-exams'),
    path('learners/exams/submit', submit_exam, name='learner-submit-exam')
]