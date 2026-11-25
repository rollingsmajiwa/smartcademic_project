from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_app.models import ParentProfile, StudentProfile
from student_app.models import AssignmentSubmission, ExamSubmission
from teachers_app.models import StudentMark

from .permissions import (
    IsAdminUserOrStaff,
    IsParentReadOnly,
    get_linked_children,
    resolve_child_for_parent,
)
from .serializers import (
    ParentAssignmentSubmissionSerializer,
    ParentChildSerializer,
    ParentExamSubmissionSerializer,
    ParentProfileDetailSerializer,
    ParentStudentMarkSerializer,
)

# Which exam counts as the "final" mark for a subject (highest priority first).
EXAM_PRIORITY = ["End Term", "Mid Term", "Opener"]


def _multiple_children_response(request, message):
    children = get_linked_children(request.user)
    return Response(
        {
            "detail": message,
            "children": ParentChildSerializer(children, many=True).data,
        },
        status=status.HTTP_200_OK,
    )


# ---------------------------------------------------------------------------
# Parent (read-only) views
# ---------------------------------------------------------------------------
class ParentMeView(APIView):
    permission_classes = [IsParentReadOnly]

    def get(self, request):
        parent_profile = getattr(request.user, "parent_profile", None)
        if not parent_profile:
            raise PermissionDenied("Parent profile not found.")
        return Response(
            ParentProfileDetailSerializer(parent_profile).data,
            status=status.HTTP_200_OK,
        )


class ParentChildrenListView(APIView):
    permission_classes = [IsParentReadOnly]

    def get(self, request):
        children = get_linked_children(request.user)
        return Response(
            {"children": ParentChildSerializer(children, many=True).data},
            status=status.HTTP_200_OK,
        )


class ParentSubmissionsView(APIView):
    permission_classes = [IsParentReadOnly]

    def get(self, request):
        child = resolve_child_for_parent(
            request.user, student_id=request.query_params.get("student_id")
        )
        if child is None:
            return _multiple_children_response(
                request,
                "Multiple children linked. Pass ?student_id=<id> to view a specific child.",
            )

        assignment_qs = (
            AssignmentSubmission.objects.filter(student=child.user)
            .select_related("assignment")
            .order_by("-submitted_at")
        )
        exam_qs = (
            ExamSubmission.objects.filter(student=child.user)
            .select_related("exam")
            .order_by("-submitted_at")
        )

        return Response(
            {
                "child": ParentChildSerializer(child).data,
                "assignments": ParentAssignmentSubmissionSerializer(
                    assignment_qs, many=True
                ).data,
                "exams": ParentExamSubmissionSerializer(exam_qs, many=True).data,
            },
            status=status.HTTP_200_OK,
        )


class ParentMarksView(APIView):
    """Read-only term and exam marks for a linked child."""

    permission_classes = [IsParentReadOnly]

    def get(self, request):
        child = resolve_child_for_parent(
            request.user, student_id=request.query_params.get("student_id")
        )
        if child is None:
            return _multiple_children_response(
                request,
                "Multiple children linked. Pass ?student_id=<id> to select a child.",
            )

        qs = StudentMark.objects.filter(student=child).order_by(
            "-year", "term", "exam_type", "subject"
        )

        term = request.query_params.get("term")
        year = request.query_params.get("year")
        exam_type = request.query_params.get("exam_type")

        if term:
            qs = qs.filter(term__iexact=term.strip())
        if year:
            try:
                qs = qs.filter(year=int(year.strip()))
            except ValueError:
                raise NotFound("Invalid year parameter.")
        if exam_type:
            qs = qs.filter(exam_type__iexact=exam_type.strip())

        return Response(
            {
                "child": ParentChildSerializer(child).data,
                "filters": {"term": term, "year": year, "exam_type": exam_type},
                "marks": ParentStudentMarkSerializer(qs, many=True).data,
            },
            status=status.HTTP_200_OK,
        )


class ParentReportCardView(APIView):
    """
    GET /api/parents/me/report-card/?student_id=...&term=Term%201&year=2026
    Aggregates a linked child's StudentMark records by subject for a term and year.
    """

    permission_classes = [IsParentReadOnly]

    def get(self, request):
        child = resolve_child_for_parent(
            request.user, student_id=request.query_params.get("student_id")
        )
        if child is None:
            return _multiple_children_response(
                request,
                "Multiple children linked. Pass ?student_id=<id> to view a report card.",
            )

        base_qs = StudentMark.objects.filter(student=child).order_by("-year", "-id")
        if not base_qs.exists():
            return Response(
                {
                    "child": ParentChildSerializer(child).data,
                    "term": request.query_params.get("term"),
                    "year": request.query_params.get("year"),
                    "subjects": [],
                    "summary": {
                        "subject_count": 0,
                        "total_marks": "0.00",
                        "average_marks": "0.00",
                    },
                },
                status=status.HTTP_200_OK,
            )

        latest = base_qs.first()
        selected_term = (request.query_params.get("term") or latest.term).strip()
        raw_year = request.query_params.get("year")
        if raw_year:
            try:
                selected_year = int(raw_year.strip())
            except ValueError:
                raise NotFound("Invalid year parameter.")
        else:
            selected_year = latest.year

        marks_qs = StudentMark.objects.filter(
            student=child,
            term__iexact=selected_term,
            year=selected_year,
        ).order_by("subject", "exam_type")

        grouped = {}
        for entry in marks_qs:
            row = grouped.setdefault(
                entry.subject,
                {
                    "subject_code": entry.subject,
                    "subject": entry.get_subject_display(),
                    "class_name": entry.class_name,
                    "exams": {},
                },
            )
            row["class_name"] = entry.class_name
            row["exams"][entry.exam_type] = str(entry.marks)

        subjects_list = []
        total = Decimal("0.00")
        for item in grouped.values():
            # Final mark = End Term, else Mid Term, else Opener.
            final = next(
                (
                    Decimal(item["exams"][key])
                    for key in EXAM_PRIORITY
                    if key in item["exams"]
                ),
                Decimal("0.00"),
            )
            total += final
            subjects_list.append(
                {
                    "subject_code": item["subject_code"],
                    "subject": item["subject"],
                    "class_name": item["class_name"],
                    "exams": item["exams"],
                    "marks": str(final),
                }
            )

        count = len(subjects_list)
        average = (
            (total / Decimal(count)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if count
            else Decimal("0.00")
        )

        return Response(
            {
                "child": ParentChildSerializer(child).data,
                "term": selected_term,
                "year": selected_year,
                "subjects": subjects_list,
                "summary": {
                    "subject_count": count,
                    "total_marks": str(
                        total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    ),
                    "average_marks": str(average),
                },
            },
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Admin views
# ---------------------------------------------------------------------------
class ManageParentChildrenSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["add", "remove", "set"], default="add")
    student_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        default=list,
    )
    admission_numbers = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        default=list,
    )

    def validate(self, attrs):
        action = attrs.get("action")
        student_ids = attrs.get("student_ids", [])
        admission_numbers = [
            adm.strip()
            for adm in attrs.get("admission_numbers", [])
            if adm and adm.strip()
        ]
        attrs["admission_numbers"] = admission_numbers

        if action in ("add", "remove") and not student_ids and not admission_numbers:
            raise serializers.ValidationError(
                "Provide at least one item in student_ids or admission_numbers."
            )
        return attrs


class AdminParentListView(ListAPIView):
    """
    GET /api/parents/admin/parents/?q=<search>
    Lists ParentProfile records with their linked children for admin selection.
    """

    permission_classes = [IsAdminUserOrStaff]
    serializer_class = ParentProfileDetailSerializer

    def get_queryset(self):
        qs = (
            ParentProfile.objects.select_related("user")
            .prefetch_related("children__user", "children__classroom")
            .order_by("user__first_name", "user__last_name", "user__username")
        )
        query = (self.request.query_params.get("q") or "").strip()
        if query:
            qs = qs.filter(
                Q(user__username__icontains=query)
                | Q(user__first_name__icontains=query)
                | Q(user__last_name__icontains=query)
                | Q(user__email__icontains=query)
                | Q(phone_number__icontains=query)
                | Q(children__admission_number__icontains=query)
            ).distinct()
        return qs


class AdminStudentSearchView(ListAPIView):
    """
    GET /api/parents/admin/students/?q=<search>
    Searches StudentProfile records by admission number, name, username, or classroom.
    """

    permission_classes = [IsAdminUserOrStaff]
    serializer_class = ParentChildSerializer

    def get_queryset(self):
        qs = StudentProfile.objects.select_related("user", "classroom").order_by(
            "admission_number", "user__first_name"
        )
        query = (self.request.query_params.get("q") or "").strip()
        if query:
            qs = qs.filter(
                Q(admission_number__icontains=query)
                | Q(user__username__icontains=query)
                | Q(user__first_name__icontains=query)
                | Q(user__last_name__icontains=query)
                | Q(surname__icontains=query)
                | Q(classroom__name__icontains=query)
            ).distinct()
        return qs[:50]


class AdminParentChildrenView(APIView):
    """
    POST /api/parents/admin/<parent_profile_id>/children/
      - "add":    link additional StudentProfile records
      - "remove": unlink specified StudentProfile records
      - "set":    replace linked children (empty list clears all)
    """

    permission_classes = [IsAdminUserOrStaff]

    def post(self, request, parent_id):
        parent_profile = get_object_or_404(
            ParentProfile.objects.select_related("user"), pk=parent_id
        )

        serializer = ManageParentChildrenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data["action"]
        student_ids = serializer.validated_data["student_ids"]
        admission_numbers = serializer.validated_data["admission_numbers"]

        matched_students = list(
            StudentProfile.objects.select_related("user", "classroom")
            .filter(Q(id__in=student_ids) | Q(admission_number__in=admission_numbers))
            .distinct()
        )

        found_ids = {s.id for s in matched_students}
        found_admissions = {
            s.admission_number.strip().lower()
            for s in matched_students
            if s.admission_number
        }

        missing_ids = [sid for sid in student_ids if sid not in found_ids]
        missing_admissions = [
            adm for adm in admission_numbers if adm.lower() not in found_admissions
        ]

        if missing_ids or missing_admissions:
            return Response(
                {
                    "detail": "One or more student profiles could not be found.",
                    "missing_student_ids": missing_ids,
                    "missing_admission_numbers": missing_admissions,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if action == "add":
            parent_profile.children.add(*matched_students)
        elif action == "remove":
            parent_profile.children.remove(*matched_students)
        elif action == "set":
            parent_profile.children.set(matched_students)

        updated_children = parent_profile.children.select_related(
            "user", "classroom"
        ).order_by("user__first_name", "admission_number")

        return Response(
            {
                "parent_profile_id": parent_profile.id,
                "parent_username": parent_profile.user.username,
                "action": action,
                "children": ParentChildSerializer(updated_children, many=True).data,
            },
            status=status.HTTP_200_OK,
        )