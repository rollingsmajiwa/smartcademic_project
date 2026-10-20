from django.urls import path
from .views import (Study_material_list_view, Assignment_list_view, Exam_list_view, Submit_assignment_view, Submit_exam_view
)

urlpatterns = [
    path('materials/', Study_material_list_view.as_view(), name='learner-materials'),
    path('assignments/', Assignment_list_view.as_view(), name='learner-assignments'),
    path('assignments/submit/', Submit_assignment_view.as_view(), name='learner-submit-assignment'),
    path('exams/', Exam_list_view.as_view(), name='learner-exams'),
    path('exams/submit', Submit_exam_view.as_view(), name='learner-submit-exam')
]