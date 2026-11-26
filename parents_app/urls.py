from django.urls import path

from .views import (
    AdminParentChildrenView,
    AdminParentListView,
    AdminStudentSearchView,
    ParentChildrenListView,
    ParentMarksView,
    ParentMeView,
    ParentReportCardView,
    ParentSubmissionsView,
    WhatsAppWebhookView,
)

urlpatterns = [
    path("me/", ParentMeView.as_view(), name="parent-me"),
    path("me/children/", ParentChildrenListView.as_view(), name="parent-children"),
    path("me/submissions/", ParentSubmissionsView.as_view(), name="parent-submissions"),
    path("me/marks/", ParentMarksView.as_view(), name="parent-marks"),
    path("me/report-card/", ParentReportCardView.as_view(), name="parent-report-card"),
    path("admin/parents/", AdminParentListView.as_view(), name="admin-parent-list"),
    path("admin/students/", AdminStudentSearchView.as_view(), name="admin-student-search"),
    path(
        "admin/<int:parent_id>/children/",
        AdminParentChildrenView.as_view(),
        name="admin-parent-children",
    ),
    path("whatsapp/webhook/", WhatsAppWebhookView.as_view(), name="parent-whatsapp-webhook"),
]