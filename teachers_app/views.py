from datetime import time
from rest_framework.decorators import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status, permissions, generics
from rest_framework.permissions import IsAuthenticated
from .models import Assignment_post, Exam_post, Teacher, TeacherAttendance, StudentMark, TeacherRevisionMaterial
from .serializers import (
    AssignmentSerializer, ExamPostSerializer, TeacherSerializer, 
    AssignmentGradeSerializer, ExamGradeSerializer, TeacherAttendanceSerializer, 
    StudentMarkSerializer, TeacherRevisionMaterialSerializer 
)
from admin_app.models import StudentProfile, TeacherProfile
from django.db.models import Avg
from student_app.models import AssignmentSubmission, ExamSubmission
from student_app.serializers import AssignmentSubmissionSerializer, ExamSubmissionSerializer

import math
from django.utils import timezone

import pandas as pd
from django.http import HttpResponse
from rest_framework.views import APIView

from collections import defaultdict
from django.shortcuts import get_object_or_404
from rest_framework.parsers import JSONParser


from .ai_service import (
    extract_text_from_file_field,
    generate_json_response,
    generate_text_response,
)
from .models import ReportFormTemplate, StudentMark, Teacher



import base64
import mimetypes

MAX_AI_REMARK_CALLS_PER_BATCH = 10

MARKING_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "suggested_score": {"type": "NUMBER"},
        "max_score": {"type": "NUMBER"},
        "feedback": {"type": "STRING"},
        "needs_manual_review": {"type": "BOOLEAN"},
        "review_reason": {"type": "STRING"},
    },
    "required": [
        "suggested_score",
        "max_score",
        "feedback",
        "needs_manual_review",
        "review_reason",
    ],
}

REPORT_COMMENT_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "class_teacher_comment": {"type": "STRING"},
        "strengths": {"type": "STRING"},
        "areas_for_improvement": {"type": "STRING"},
        "principal_remark": {"type": "STRING"},
    },
    "required": [
        "class_teacher_comment",
        "strengths",
        "areas_for_improvement",
        "principal_remark",
    ],
}


def _file_to_data_uri(uploaded_file) -> str:
    if not uploaded_file:
        return ""
    name = getattr(uploaded_file, "name", "").lower()
    if not name.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
        return ""
    mime_type, _ = mimetypes.guess_type(name)
    mime_type = mime_type or "image/png"
    uploaded_file.seek(0)
    raw = uploaded_file.read()
    uploaded_file.seek(0)
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def build_school_report_html(logo_src: str = "/ngegu-logo.png") -> str:
    logo_html = (
        f'<img src="{logo_src}" alt="Ngegu School Logo" '
        f'style="width:72px;height:72px;object-fit:contain;" />'
        if logo_src
        else ""
    )

    return f"""
<div style="font-family: 'Times New Roman', Georgia, serif; color: #111; max-width: 820px; margin: 0 auto; padding: 20px; background: #fff;">
  <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #111; padding-bottom: 10px;">
    <div style="width: 78px;">{logo_html}</div>
    <div style="text-align: center; flex: 1;">
      <div style="font-size: 11px; font-weight: bold; letter-spacing: 1px;">HARD WORK PAYS</div>
      <div style="font-size: 19px; font-weight: bold; margin-top: 2px;">NGEGU PRIMARY &amp; JUNIOR SCHOOL</div>
      <div style="font-size: 13px; font-weight: bold;">P.O. BOX 345-00900</div>
      <div style="font-size: 14px; font-weight: bold;">KIAMBU.</div>
      <div style="font-size: 15px; font-weight: bold; margin-top: 6px; text-decoration: underline;">ASSESSMENT REPORT</div>
    </div>
    <div style="width: 78px;"></div>
  </div>

  <div style="margin-top: 12px; font-size: 13px; line-height: 1.6;">
    <div><strong>ACADEMIC YEAR:</strong> {{{{year}}}} &nbsp;&nbsp;&nbsp; <strong>TERM:</strong> {{{{term}}}} &nbsp;&nbsp;&nbsp; <strong>GRADE:</strong> {{{{class_name}}}}</div>
    <div><strong>NAME:</strong> <span style="text-transform: uppercase; font-weight: bold;">{{{{student_name}}}}</span> &nbsp;&nbsp;&nbsp; <strong>POSITION:</strong> <span style="font-weight: bold;">{{{{position}}}}</span></div>
  </div>

  <table style="width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 12px;">
    <thead>
      <tr style="background: #f3f4f6;">
        <th style="border: 1px solid #222; padding: 6px 8px; text-align: left;">LEARNING AREA</th>
        <th style="border: 1px solid #222; padding: 6px 8px; text-align: left;">SCORE</th>
      </tr>
    </thead>
    <tbody>
      {{{{performance_rows_html}}}}
      <tr style="font-weight: bold; background: #fafafa;">
        <td style="border: 1px solid #222; padding: 6px 8px;">TOTAL MARKS</td>
        <td style="border: 1px solid #222; padding: 6px 8px;">{{{{total_marks}}}} &nbsp;(Mean: {{{{mean_score}}}}%)</td>
      </tr>
      <tr style="font-weight: bold; background: #fafafa;">
        <td style="border: 1px solid #222; padding: 6px 8px;">POSITION</td>
        <td style="border: 1px solid #222; padding: 6px 8px;">{{{{position}}}}</td>
      </tr>
    </tbody>
  </table>

  <div style="margin-top: 14px; font-size: 12.5px; line-height: 1.5;">
    <div style="font-weight: bold; margin-bottom: 4px;">CLASSTEACHER'S REMARKS:</div>
    <p style="margin: 0 0 8px;">{{{{class_teacher_comment}}}}</p>
    <p style="margin: 0 0 6px;"><strong>Strengths:</strong> {{{{strengths}}}} &nbsp;|&nbsp; <strong>Areas for Improvement:</strong> {{{{areas_for_improvement}}}}</p>
    <p style="margin: 0 0 10px;"><strong>Principal's Remark:</strong> {{{{principal_remark}}}}</p>
    <div style="font-size: 11.5px; font-weight: bold;">
      CLOSING DATE: 21ST OCTOBER, 2026. &nbsp;&nbsp;&nbsp; FIRST TERM BEGINS ON: MONDAY 4TH JANUARY, 2027.
    </div>
  </div>

  <table style="width: 100%; border-collapse: collapse; margin-top: 14px; font-size: 11px;">
    <thead>
      <tr style="background: #f3f4f6;">
        <th style="border: 1px solid #222; padding: 4px 6px; text-align: left;">PERFORMANCE LEVEL</th>
        <th style="border: 1px solid #222; padding: 4px 6px; text-align: left;">ACTUAL PERFORMANCE LEVEL</th>
        <th style="border: 1px solid #222; padding: 4px 6px; text-align: left;">RAW MARKS</th>
      </tr>
    </thead>
    <tbody>
      <tr><td style="border: 1px solid #222; padding: 3px 6px;" rowspan="2">EXCEEDING EXPECTATION</td><td style="border: 1px solid #222; padding: 3px 6px;">EE1</td><td style="border: 1px solid #222; padding: 3px 6px;">90-99</td></tr>
      <tr><td style="border: 1px solid #222; padding: 3px 6px;">EE2</td><td style="border: 1px solid #222; padding: 3px 6px;">75-89</td></tr>
      <tr><td style="border: 1px solid #222; padding: 3px 6px;" rowspan="2">MEETING EXPECTATION</td><td style="border: 1px solid #222; padding: 3px 6px;">ME1</td><td style="border: 1px solid #222; padding: 3px 6px;">58-74</td></tr>
      <tr><td style="border: 1px solid #222; padding: 3px 6px;">ME2</td><td style="border: 1px solid #222; padding: 3px 6px;">41-57</td></tr>
      <tr><td style="border: 1px solid #222; padding: 3px 6px;" rowspan="2">APPROACHING EXPECTATION</td><td style="border: 1px solid #222; padding: 3px 6px;">AE1</td><td style="border: 1px solid #222; padding: 3px 6px;">31-40</td></tr>
      <tr><td style="border: 1px solid #222; padding: 3px 6px;">AE2</td><td style="border: 1px solid #222; padding: 3px 6px;">21-30</td></tr>
      <tr><td style="border: 1px solid #222; padding: 3px 6px;" rowspan="2">BELOW EXPECTATION</td><td style="border: 1px solid #222; padding: 3px 6px;">BE1</td><td style="border: 1px solid #222; padding: 3px 6px;">11-20</td></tr>
      <tr><td style="border: 1px solid #222; padding: 3px 6px;">BE2</td><td style="border: 1px solid #222; padding: 3px 6px;">1-10</td></tr>
    </tbody>
  </table>

  <div style="display: flex; justify-content: space-between; font-size: 10.5px; color: #444; margin-top: 10px; border-top: 1px solid #ccc; padding-top: 4px;">
    <span>Ngegu Primary &amp; Junior School - Academic Report</span>
    <span>Page 1 of 1</span>
  </div>
</div>
""".strip()


DEFAULT_REPORT_HTML = build_school_report_html()


def _fallback_remarks_for_student(
    student_name: str,
    mean_score: float,
    position_label: str,
    term: str,
    year: int,
    records,
):
    sorted_records = sorted(records, key=lambda r: float(r.marks), reverse=True)
    top_subjects = ", ".join(
        f"{r.get_subject_display()} ({float(r.marks):.1f}%)" for r in sorted_records[:2]
    )
    weak_records = [r for r in records if float(r.marks) < 58]
    weak_subjects = ", ".join(
        f"{r.get_subject_display()} ({float(r.marks):.1f}%)" for r in weak_records[:2]
    )

    return {
        "class_teacher_comment": (
            f"{student_name} ranked {position_label} with a mean score of {mean_score}% in {term} {year}. "
            + (f"Strongest areas include {top_subjects}. " if top_subjects else "")
            + (
                f"Focus extra revision on {weak_subjects}."
                if weak_subjects
                else "Keep maintaining consistent effort across all learning areas."
            )
        ),
        "strengths": top_subjects or "Consistent participation across learning areas.",
        "areas_for_improvement": (
            f"Targeted practice in {weak_subjects}"
            if weak_subjects
            else "Continue regular revision and assessment practice."
        ),
        "principal_remark": (
            f"Commendable performance ({position_label}) for {student_name} in {term} {year}; aim even higher next term."
            if mean_score >= 58
            else f"Encouraged to stay focused and work closely with teachers to improve on position {position_label}."
        ),
    }


class AISuggestMarkView(APIView):
    """Generates a draft mark & feedback for teacher review (human-in-the-loop)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        submission_type = (request.data.get("submission_type") or "assignment").lower()
        submission_id = request.data.get("submission_id")
        max_score = float(request.data.get("max_score", 100))

        if not submission_id:
            return Response(
                {"error": "submission_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if submission_type == "exam":
            sub = get_object_or_404(ExamSubmission, id=submission_id)
            task_title = getattr(sub.exam, "title", "Exam")
            task_desc = getattr(sub.exam, "description", "") or ""
            task_file_text = extract_text_from_file_field(
                getattr(sub.exam, "file", None), max_chars=4000
            )
            answers_json_text = (
                str(sub.answers_json) if getattr(sub, "answers_json", None) else ""
            )
        else:
            sub = get_object_or_404(AssignmentSubmission, id=submission_id)
            task_title = getattr(sub.assignment, "title", "Assignment")
            task_desc = getattr(sub.assignment, "description", "") or ""
            task_file_text = extract_text_from_file_field(
                getattr(sub.assignment, "file", None), max_chars=4000
            )
            answers_json_text = ""

        student_text = (getattr(sub, "answer_text", "") or "").strip()
        student_file_text = extract_text_from_file_field(
            getattr(sub, "file", None), max_chars=8000
        )
        combined_answer = "\n\n".join(
            part for part in [student_text, answers_json_text, student_file_text] if part
        ).strip()

        if not combined_answer:
            sub.ai_needs_manual_review = True
            sub.ai_feedback = (
                "No readable text found in submission. Please review the uploaded file manually."
            )
            sub.ai_marked_at = timezone.now()
            sub.save()
            return Response(
                {
                    "suggested_score": 0,
                    "max_score": max_score,
                    "feedback": sub.ai_feedback,
                    "needs_manual_review": True,
                },
                status=status.HTTP_200_OK,
            )

        system_instruction = (
            "You are an assistive grading helper for SmartAcademic. "
            "Evaluate the learner's submission against the assignment or exam instructions and "
            "propose a fair draft score and constructive feedback for teacher review. "
            "Never exceed max_score. Set needs_manual_review=true if the response is incomplete, "
            "unclear, or needs teacher judgment."
        )
        prompt = (
            f"Title: {task_title}\n"
            f"Instructions: {task_desc}\n"
            f"Question Paper Content: {task_file_text}\n"
            f"Maximum Score: {max_score}\n\n"
            f"Learner Submission:\n{combined_answer}"
        )

        try:
            result = generate_json_response(
                system_instruction, prompt, MARKING_SCHEMA, temperature=0.2
            )
            score = round(
                max(0.0, min(max_score, float(result.get("suggested_score", 0)))), 2
            )
            feedback = (result.get("feedback") or "").strip()
            needs_review = bool(result.get("needs_manual_review", False))
            reason = (result.get("review_reason") or "").strip()
            full_feedback = (
                f"{feedback} (Note: {reason})" if needs_review and reason else feedback
            )

            sub.ai_suggested_score = score
            sub.ai_feedback = full_feedback
            sub.ai_needs_manual_review = needs_review
            sub.ai_marked_at = timezone.now()
            sub.save()

            return Response(
                {
                    "suggested_score": score,
                    "max_score": max_score,
                    "feedback": full_feedback,
                    "needs_manual_review": needs_review,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            return Response(
                {"error": f"AI marking could not complete: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


def _resolve_report_template(user):
    tmpl = (
        ReportFormTemplate.objects.filter(created_by=user)
        .order_by("-updated_at")
        .first()
    )
    if not tmpl:
        tmpl = (
            ReportFormTemplate.objects.filter(is_default_template=True)
            .order_by("-updated_at")
            .first()
            or ReportFormTemplate.objects.order_by("-updated_at").first()
        )
    return tmpl


def _get_active_html_for_template(tmpl, request=None) -> str:
    logo_src = "/ngegu-logo.png"
    if tmpl and getattr(tmpl, "template_file", None):
        data_uri = _file_to_data_uri(tmpl.template_file)
        if data_uri:
            logo_src = data_uri
        elif request is not None and tmpl.template_file.name.lower().endswith(
            (".png", ".jpg", ".jpeg", ".webp", ".gif")
        ):
            logo_src = request.build_absolute_uri(tmpl.template_file.url)

    if not tmpl or tmpl.use_default_template:
        return build_school_report_html(logo_src=logo_src)
    if tmpl.custom_html_template:
        return tmpl.custom_html_template
    return build_school_report_html(logo_src=logo_src)


class ReportTemplateView(APIView):
    """Option 1: Exact Ngegu school report template (default). Option 2: Optional AI edit."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        tmpl = _resolve_report_template(request.user)
        if not tmpl:
            return Response(
                {
                    "use_default_template": True,
                    "is_default_template": True,
                    "title": "Ngegu Primary & Junior School Assessment Report",
                    "html_template": DEFAULT_REPORT_HTML,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "id": tmpl.id,
                "title": tmpl.title,
                "use_default_template": tmpl.use_default_template,
                "is_default_template": getattr(tmpl, "is_default_template", True),
                "template_file_name": (
                    tmpl.template_file.name.split("/")[-1] if tmpl.template_file else None
                ),
                "html_template": _get_active_html_for_template(tmpl, request=request),
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        teacher = Teacher.objects.filter(user=request.user).first()
        tmpl = _resolve_report_template(request.user)
        if not tmpl:
            tmpl = ReportFormTemplate.objects.create(
                created_by=request.user,
                teacher=teacher,
                title="Ngegu Primary & Junior School Assessment Report",
                custom_html_template=DEFAULT_REPORT_HTML,
                use_default_template=True,
                is_default_template=True,
            )
        elif tmpl.created_by != request.user:
            tmpl = ReportFormTemplate.objects.create(
                created_by=request.user,
                teacher=teacher,
                title=tmpl.title,
                template_file=tmpl.template_file,
                custom_html_template=tmpl.custom_html_template or DEFAULT_REPORT_HTML,
                use_default_template=tmpl.use_default_template,
                is_default_template=True,
            )

        if request.data.get("title"):
            tmpl.title = request.data.get("title")

        if "template_file" in request.FILES:
            tmpl.template_file = request.FILES["template_file"]
            tmpl.title = tmpl.template_file.name.split("/")[-1]
            if hasattr(tmpl, "is_default_template"):
                tmpl.is_default_template = True
            tmpl.custom_html_template = _get_active_html_for_template(tmpl, request=request)

        if str(request.data.get("use_default_template")).lower() == "true":
            tmpl.use_default_template = True
            if hasattr(tmpl, "is_default_template"):
                tmpl.is_default_template = True
            tmpl.custom_html_template = _get_active_html_for_template(tmpl, request=request)

        # Option 2: Only invoke AI when an explicit edit instruction is provided
        ai_instruction = (request.data.get("ai_edit_instruction") or "").strip()
        if ai_instruction:
            base_html = _get_active_html_for_template(tmpl, request=request)
            system_instruction = (
                "You are a report card layout assistant for Ngegu Primary & Junior School. "
                "Apply only the requested layout change while preserving the school name "
                "(NGEGU PRIMARY & JUNIOR SCHOOL), address (P.O. BOX 345-00900, KIAMBU.), "
                "motto (HARD WORK PAYS), logo image, CBC grading table, and all placeholders: "
                "{{student_name}}, {{class_name}}, {{term}}, {{year}}, {{position}}, {{mean_score}}, "
                "{{total_marks}}, {{performance_rows_html}}, {{performance_summary}}, {{strengths}}, "
                "{{areas_for_improvement}}, {{class_teacher_comment}}, {{principal_remark}}. "
                "Return ONLY valid HTML with inline styles."
            )
            try:
                edited = generate_text_response(
                    system_instruction,
                    f"Instruction: {ai_instruction}\n\nCurrent HTML:\n{base_html}",
                    temperature=0.2,
                )
                tmpl.custom_html_template = (
                    edited.replace("```html", "").replace("```", "").strip()
                )
                tmpl.use_default_template = False
                if hasattr(tmpl, "is_default_template"):
                    tmpl.is_default_template = True
            except Exception as exc:
                return Response(
                    {"error": f"AI template edit failed: {exc}"},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

        tmpl.save()
        return Response(
            {
                "id": tmpl.id,
                "title": tmpl.title,
                "use_default_template": tmpl.use_default_template,
                "is_default_template": getattr(tmpl, "is_default_template", True),
                "template_file_name": (
                    tmpl.template_file.name.split("/")[-1] if tmpl.template_file else None
                ),
                "html_template": _get_active_html_for_template(tmpl, request=request),
            },
            status=status.HTTP_200_OK,
        )


class GenerateStudentReportFormsView(APIView):
    """Generates student report forms using the Ngegu school layout, class analysis ranks, and remarks."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        class_name = request.data.get("class_name", "Grade 7")
        term = request.data.get("term", "Term 1")
        year = int(request.data.get("year", 2026))

        marks_qs = StudentMark.objects.filter(
            class_name=class_name,
            term=term,
            year=year,
        ).select_related("student")

        if not marks_qs.exists():
            return Response(
                {"error": f"No analyzed marks found for {class_name} ({term} {year})."},
                status=status.HTTP_404_NOT_FOUND,
            )

        grouped = defaultdict(list)
        for mark in marks_qs:
            grouped[mark.student].append(mark)

        ranked_students = []
        for student_profile, records in grouped.items():
            total_raw = sum(float(r.marks) for r in records)
            mean_score = round(total_raw / len(records), 1)
            ranked_students.append((student_profile, records, total_raw, mean_score))

        ranked_students.sort(key=lambda entry: (entry[2], entry[3]), reverse=True)
        class_size = len(ranked_students)

        positions_by_student_id = {}
        current_rank = 0
        previous_total = None
        for idx, (student_profile, _, total_raw, _) in enumerate(ranked_students, start=1):
            rounded_total = round(total_raw, 2)
            if previous_total is None or rounded_total < previous_total:
                current_rank = idx
                previous_total = rounded_total
            positions_by_student_id[student_profile.id] = f"{current_rank}/{class_size}"

        tmpl = _resolve_report_template(request.user)
        active_html = _get_active_html_for_template(tmpl, request=request)

        system_instruction = (
            "You are an experienced school academic advisor writing individualized report form comments. "
            "Base every comment strictly on the learner's subject scores, class position, and mean score."
        )

        reports = []
        for idx, (student_profile, records, total_raw, mean_score) in enumerate(ranked_students):
            student_name = str(student_profile)
            position_label = positions_by_student_id[student_profile.id]
            row_items = []
            subject_lines = []

            for r in records:
                score_val = float(r.marks)
                subject_label = r.get_subject_display()
                subject_lines.append(f"{subject_label}: {score_val:.1f}%")
                row_items.append(
                    f"<tr>"
                    f"<td style='border:1px solid #222;padding:5px 8px;'>{subject_label}</td>"
                    f"<td style='border:1px solid #222;padding:5px 8px;'>{score_val:.1f}%</td>"
                    f"</tr>"
                )

            total_marks_text = f"{total_raw:.1f} / {len(records) * 100}"
            performance_rows_html = "\n".join(row_items)
            summary_text = " | ".join(subject_lines)

            fallback = _fallback_remarks_for_student(
                student_name, mean_score, position_label, term, year, records
            )

            if idx < MAX_AI_REMARK_CALLS_PER_BATCH:
                prompt = (
                    f"Student: {student_name}\n"
                    f"Class: {class_name}, {term} {year}\n"
                    f"Position: {position_label}\n"
                    f"Total Marks: {total_marks_text} (Mean: {mean_score}%)\n"
                    f"Subject Performance: {summary_text}"
                )
                try:
                    ai_remarks = generate_json_response(
                        system_instruction, prompt, REPORT_COMMENT_SCHEMA, temperature=0.3
                    )
                    remarks = {
                        "class_teacher_comment": (
                            ai_remarks.get("class_teacher_comment") or fallback["class_teacher_comment"]
                        ).strip(),
                        "strengths": (
                            ai_remarks.get("strengths") or fallback["strengths"]
                        ).strip(),
                        "areas_for_improvement": (
                            ai_remarks.get("areas_for_improvement") or fallback["areas_for_improvement"]
                        ).strip(),
                        "principal_remark": (
                            ai_remarks.get("principal_remark") or fallback["principal_remark"]
                        ).strip(),
                    }
                except Exception:
                    remarks = fallback
            else:
                remarks = fallback

            rendered_html = active_html
            replacements = {
                "{{student_name}}": student_name,
                "{{class_name}}": class_name,
                "{{term}}": term,
                "{{year}}": str(year),
                "{{position}}": position_label,
                "{{mean_score}}": str(mean_score),
                "{{total_marks}}": total_marks_text,
                "{{performance_rows_html}}": performance_rows_html,
                "{{performance_summary}}": summary_text,
                "{{strengths}}": remarks["strengths"],
                "{{areas_for_improvement}}": remarks["areas_for_improvement"],
                "{{class_teacher_comment}}": remarks["class_teacher_comment"],
                "{{principal_remark}}": remarks["principal_remark"],
            }
            for placeholder, value in replacements.items():
                rendered_html = rendered_html.replace(placeholder, value)

            reports.append(
                {
                    "student_id": student_profile.id,
                    "name": student_name,
                    "class_name": class_name,
                    "term": term,
                    "year": year,
                    "position": position_label,
                    "mean_score": mean_score,
                    "total_marks": total_marks_text,
                    "performance_summary": summary_text,
                    **remarks,
                    "rendered_html": rendered_html,
                }
            )

        return Response({"reports": reports}, status=status.HTTP_200_OK)

# API endpoint to list teachers
class TeacherListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        teachers = Teacher.objects.all()
        data = [{"id": t.id, "name": str(t)} for t in teachers]
        return Response(data)

# API for revision materials
class TeacherRevisionsView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def get(self, request):
        materials = TeacherRevisionMaterial.objects.all().order_by('-uploaded_at')
        serializer = TeacherRevisionMaterialSerializer(materials, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = TeacherRevisionMaterialSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
# Teachers overview API
class TeacherOverviewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            teacher_profile = Teacher.objects.get(user=request.user)
        except Teacher.DoesNotExist:
            if request.user.is_staff or request.user.is_superuser:
                assignments = Assignment_post.objects.all()
                exams = Exam_post.objects.all() if 'Exam_post' in globals() else Assignment_post.objects.none()
                assignment_subs = AssignmentSubmission.objects.filter(assignment__in=assignments)
                exam_subs = ExamSubmission.objects.filter(exam__in=exams) if 'ExamSubmission' in globals() else AssignmentSubmission.objects.none()
                
                pending_assignments = assignment_subs.filter(grade__isnull=True).count()
                pending_exams = exam_subs.filter(score__isnull=True).count() if 'ExamSubmission' in globals() else 0

                return Response({
                    "total_assignments_posted": assignments.count(),
                    "assignments_posted": assignments.count(),
                    "total_exams_created": exams.count(),
                    "exams_created": exams.count(),
                    "total_submissions_received": assignment_subs.count() + exam_subs.count(),
                    "submissions_received": assignment_subs.count() + exam_subs.count(),
                    "pending_grades": pending_assignments + pending_exams
                })
            else:
                teacher_profile = Teacher.objects.create(user=request.user)

        assignments = Assignment_post.objects.filter(teacher=teacher_profile)
        exams = Exam_post.objects.filter(teacher=teacher_profile) if 'Exam_post' in globals() else Assignment_post.objects.none()

        assignment_subs = AssignmentSubmission.objects.filter(assignment__in=assignments)
        exam_subs = ExamSubmission.objects.filter(exam__in=exams) if 'ExamSubmission' in globals() else AssignmentSubmission.objects.none()

        pending_assignments = assignment_subs.filter(grade__isnull=True).count()
        pending_exams = exam_subs.filter(score__isnull=True).count() if 'ExamSubmission' in globals() else 0

        data = {
            "total_assignments_posted": assignments.count(),
            "assignments_posted": assignments.count(),
            "total_exams_created": exams.count(),
            "exams_created": exams.count(),
            "total_submissions_received": assignment_subs.count() + exam_subs.count(),
            "submissions_received": assignment_subs.count() + exam_subs.count(),
            "pending_grades": pending_assignments + pending_exams
        }
        return Response(data)

class Teacher_assignments_view(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, *args, **kwargs):
        assignments = Assignment_post.objects.all()
        serializer = AssignmentSerializer(assignments, many=True)
        return Response(serializer.data)
    
    def post(self, request, *args, **kwargs):
        try:
            teacher_profile = Teacher.objects.get(user=request.user)
        except Teacher.DoesNotExist:
            return Response({"error": "teacher profile not found"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = AssignmentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(teacher=teacher_profile)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Teachers to view assignment submissions with full typed answers & student details
class TeacherAssignmentSubmissionView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        try:
            teacher = request.user.teacher_profile
            submissions = AssignmentSubmission.objects.filter(assignment__teacher=teacher)
            serializer = AssignmentGradeSerializer(submissions, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except AttributeError:
            return Response({"error": "This user has no teacher profile"}, status=status.HTTP_400_BAD_REQUEST)

# Teachers to view exam submissions with full typed answers & student details
class TeacherExamSubmissionView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        try:
            teacher = request.user.teacher_profile
            submissions = ExamSubmission.objects.filter(exam__teacher=teacher)
            serializer = ExamGradeSerializer(submissions, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except AttributeError:
            return Response({"error": "This user has no teacher profile"}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, *args, **kwargs):
        serializer = ExamSubmissionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(student=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# View for teachers to grade submitted assignments (saves grades & qualitative reviews)
class AssignmentGradeSubmissionView(generics.UpdateAPIView):
    queryset = AssignmentSubmission.objects.all()
    serializer_class = AssignmentGradeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save()

# View for teachers to grade submitted exams (saves grades & qualitative reviews)
class ExamGradeSubmissionView(generics.UpdateAPIView):
    queryset = ExamSubmission.objects.all()
    serializer_class = ExamGradeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save()

class Teacher_exams_view(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, *args, **kwargs):
        exams = Exam_post.objects.all()
        serializer = ExamPostSerializer(exams, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        try:
            teacher_profile = Teacher.objects.get(user=request.user)
        except Teacher.DoesNotExist:
            teacher_profile = Teacher.objects.create(user=request.user)

        serializer = ExamPostSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(teacher=teacher_profile)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Teacher profile view
class Teacher_profile_view(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, pk, *args, **kwargs):
        try:
            teacher = Teacher.objects.get(pk=pk)
        except Teacher.DoesNotExist:
            return Response({'error': 'Teacher profile not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = TeacherSerializer(teacher)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def put(self, request, pk, *args, **kwargs):
        try:
            teacher = Teacher.objects.get(pk=pk)
        except Teacher.DoesNotExist:
            return Response({'error': 'Teacher profile not found'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = TeacherSerializer(teacher, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ==========================================
# TEACHER GPS ATTENDANCE SYSTEM
# ==========================================

# School GPS coordinates
LAT_FENCE = -1.2647
LON_FENCE = 36.8101

# Allowed distance from school: 500 metres
RADIUS_METERS = 20000

# Attendance cutoff
ON_TIME_CUTOFF = time(7, 0)


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two GPS coordinates
    using the Haversine formula.
    Returns distance in metres.
    """

    earth_radius = 6371000

    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return earth_radius * c


class GeoFenceAttendanceView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        # Get submitted information
        teacher_tsc_id = request.data.get('tsc_number')
        direction = request.data.get('direction', 'in').lower()

        user_lat = request.data.get('latitude')
        user_lon = request.data.get('longitude')

        # ==================================
        # VALIDATE INPUT
        # ==================================

        if not teacher_tsc_id:
            return Response(
                {"error": "Teacher TSC Number is required!"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if direction not in ['in', 'out']:
            return Response(
                {"error": "Direction must be either 'in' or 'out'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if user_lat is None or user_lon is None:
            return Response(
                {"error": "GPS coordinates are required!"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user_lat = float(user_lat)
            user_lon = float(user_lon)

            if not (
                math.isfinite(user_lat)
                and math.isfinite(user_lon)
                and -90 <= user_lat <= 90
                and -180 <= user_lon <= 180
            ):
                raise ValueError

        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid GPS coordinates."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ==================================
        # FIND TEACHER
        # ==================================

        try:
            teacher = TeacherProfile.objects.get(
                tsc_number=teacher_tsc_id
            )

        except TeacherProfile.DoesNotExist:
            return Response(
                {"error": "Teacher not found with this TSC Number!"},
                status=status.HTTP_404_NOT_FOUND
            )

        # ==================================
        # VERIFY SCHOOL LOCATION
        # ==================================

        distance = calculate_distance(
            user_lat,
            user_lon,
            LAT_FENCE,
            LON_FENCE
        )

        is_inside = distance <= RADIUS_METERS

        # ==================================
        # GET CURRENT DATE AND TIME
        # ==================================

        current_time = timezone.localtime()
        today = current_time.date()

        # ==================================
        # GET TODAY'S ATTENDANCE RECORD
        # ==================================

        attendance = TeacherAttendance.objects.filter(
            teacher=teacher,
            date=today
        ).first()

        # ==================================
        # HANDLE AUTOMATIC CLOCK-OUT
        # ==================================

        if not is_inside:

            if (
                attendance
                and attendance.check_in_time
                and not attendance.check_out_time
            ):

                attendance.check_out_time = current_time

                attendance.save(
                    update_fields=['check_out_time']
                )

                return Response({
                    "success": True,
                    "message": "You left the school compound. Automatically clocked OUT.",
                    "time": current_time,
                    "status": attendance.status
                }, status=status.HTTP_200_OK)

            return Response({
                "error": "You are outside the school compound.",
                "distance_metres": round(distance, 2)
            }, status=status.HTTP_400_BAD_REQUEST)

        # ==================================
        # CREATE TODAY'S ATTENDANCE RECORD
        # ==================================

        if attendance is None:

            attendance = TeacherAttendance.objects.create(
                teacher=teacher,
                date=today,
                status='Absent'
            )

        # ==================================
        # HANDLE CLOCK-IN
        # ==================================

        if direction == 'in':

            if attendance.check_in_time:

                return Response({
                    "error": "You have already clocked in today.",
                    "status": attendance.status
                }, status=status.HTTP_400_BAD_REQUEST)

            attendance.check_in_time = current_time

            # Before or exactly 7:00 AM = Present
            # After 7:00 AM = Late

            if current_time.time() > ON_TIME_CUTOFF:

                attendance.status = 'Late'

            else:

                attendance.status = 'Present'

            attendance.save(
                update_fields=[
                    'check_in_time',
                    'status'
                ]
            )

        # ==================================
        # HANDLE CLOCK-OUT
        # ==================================

        elif direction == 'out':

            if not attendance.check_in_time:

                return Response({
                    "error": "You must clock in before clocking out."
                }, status=status.HTTP_400_BAD_REQUEST)

            if attendance.check_out_time:

                return Response({
                    "error": "You have already clocked out today."
                }, status=status.HTTP_400_BAD_REQUEST)

            attendance.check_out_time = current_time

            attendance.save(
                update_fields=['check_out_time']
            )

        # ==================================
        # SUCCESS RESPONSE
        # ==================================

        return Response({

            "success": True,

            "message": (
                "Successfully clocked IN."
                if direction == 'in'
                else "Successfully clocked OUT."
            ),

            "teacher": str(teacher),

            "date": today,

            "time": current_time,

            "distance_metres": round(distance, 2),

            "status": attendance.status,

            "check_in_time": attendance.check_in_time,

            "check_out_time": attendance.check_out_time

        }, status=status.HTTP_200_OK)

class ClassGradeTableView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, class_name, term):
        students = StudentProfile.objects.filter(classroom__name=class_name)
        
        subjects = [
            {"key": "maths", "label": "Maths"},
            {"key": "kiswahili", "label": "Kiswahili"},
            {"key": "english", "label": "English"},
            {"key": "pretechnical_studies", "label": "Pre-Technical Studies"},
            {"key": "integrated_science", "label": "Integrated Science"},
            {"key": "social_studies", "label": "Social Studies"},
            {"key": "cre", "label": "CRE"},
            {"key": "arts", "label": "Arts"},
            {"key": "agriculture", "label": "Agriculture"}
        ]

        table_data = []
        for student in students:
            student_name = student.user.get_full_name() or student.user.username
            marks_qs = StudentMark.objects.filter(student=student, class_name=class_name, term=term, year=2026)
            marks_dict = {m.subject: float(m.marks) for m in marks_qs}

            student_row = {
                "student_id": student.id,
                "admission_number": student.admission_number,
                "student_name": student_name,
                "marks": {sub["key"]: marks_dict.get(sub["key"], 0.0) for sub in subjects}
            }
            table_data.append(student_row)

        return Response({
            "class_name": class_name,
            "term": term,
            "year": 2026,
            "subjects": subjects,
            "students_table": table_data
        }, status=status.HTTP_200_OK)


class BulkMarkSaveView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        data = request.data
        class_name = data.get('class_name')
        term = data.get('term')
        entries = data.get('entries', [])
        
        teacher = getattr(request.user, 'teacher_profile', None)

        for entry in entries:
            StudentMark.objects.update_or_create(
                student_id=entry.get('student_id'),
                subject=entry.get('subject'),
                class_name=class_name,
                term=term,
                year=2026,
                defaults={
                    'marks': entry.get('marks', 0.0), 
                    'teacher': teacher
                }
            )

        return Response({"detail": "Marks saved successfully!"}, status=status.HTTP_200_OK)


from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
def get_grade_level(score):
    if score is None:
        return "-"
    if score >= 90:
        return "EE1"
    if score >= 75:
        return "EE2"
    if score >= 58:
        return "ME1"
    if score >= 41:
        return "ME2"
    if score >= 31:
        return "AE1"
    if score >= 21:
        return "AE2"
    if score >= 11:
        return "BE1"
    return "BE2"

SUBJECT_SHORT = {
    'maths': 'Maths', 'kiswahili': 'Kiswahili', 'english': 'English',
    'pretechnical_studies': 'Pre-Tech', 'integrated_science': 'Int. Sci',
    'social_studies': 'Soc. Studies', 'cre': 'CRE', 'arts': 'Arts',
    'agriculture': 'Agric',
}


class ClassAnalysisView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    SUBJECTS = [
        'maths', 'kiswahili', 'english', 'pretechnical_studies',
        'integrated_science', 'social_studies', 'cre', 'arts', 'agriculture'
    ]

    def get(self, request, class_name, term):
        subjects = self.SUBJECTS
        marks_qs = StudentMark.objects.filter(class_name=class_name, term=term, year=2026)
        export = request.GET.get('export')

        if not marks_qs.exists():
            if export:
                return Response({"detail": "No marks saved for this class and term yet."},
                                status=status.HTTP_404_NOT_FOUND)
            # Not an error: the teacher just has not entered marks yet
            return Response({
                "class_name": class_name, "term": term, "year": 2026,
                "subject_columns": subjects,
                "student_performance_table": [],
                "subject_means": {}, "total_class_mean": 0.0,
            }, status=status.HTTP_200_OK)

        # Keyed by student id, so two students with the same name are not merged
        students_data = {}
        for record in marks_qs.select_related('student', 'student__user'):
            sid = record.student_id
            if sid not in students_data:
                name = record.student.user.get_full_name() or record.student.user.username
                students_data[sid] = {
                    "admission_number": record.student.admission_number,
                    "name": name,
                    "subjects": {sub: {"score": 0.0, "level": "BE"} for sub in subjects},
                    "total_marks": 0.0,
                }
            score = float(record.marks)
            students_data[sid]["subjects"][record.subject] = {
                "score": score, "level": get_grade_level(score),
            }
            students_data[sid]["total_marks"] += score

        student_list = sorted(students_data.values(), key=lambda x: x["total_marks"], reverse=True)
        for rank, student in enumerate(student_list, start=1):
            student["rank"] = rank

        subject_means = {}
        for sub in subjects:
            avg = marks_qs.filter(subject=sub).aggregate(Avg('marks'))['marks__avg']
            subject_means[sub] = round(float(avg), 2) if avg else 0.0

        # Total class mean = sum of every learner's total marks / number of learners
        total_class_mean = (
        round(sum(s["total_marks"] for s in student_list) / len(student_list), 2)
        if student_list else 0.0
        )

        if export == 'pdf':
            return self.export_to_pdf(student_list, subjects, subject_means,
                                      total_class_mean, class_name, term)

        return Response({
            "class_name": class_name, "term": term, "year": 2026,
            "subject_columns": subjects,
            "student_performance_table": student_list,
            "subject_means": subject_means,
            "total_class_mean": total_class_mean,
        }, status=status.HTTP_200_OK)

    def export_to_pdf(self, student_list, subjects, subject_means, total_class_mean, class_name, term):
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=landscape(A4),
            leftMargin=24, rightMargin=24, topMargin=24, bottomMargin=24,
        )
        styles = getSampleStyleSheet()
        elements = [
            Paragraph(f"Class Performance Report: {class_name}, {term} 2026", styles['Title']),
            Paragraph(f"Students: {len(student_list)} &nbsp;&nbsp; Class mean: {total_class_mean}", styles['Normal']),
            Spacer(1, 12),
        ]

        data = [['Rank', 'Adm No', 'Student'] + [SUBJECT_SHORT.get(s, s) for s in subjects] + ['Total']]
        for s in student_list:
            row = [s["rank"], s["admission_number"], s["name"]]
            for sub in subjects:
                d = s["subjects"][sub]
                row.append(f"{d['score']:g} {d['level']}")
            row.append(f"{s['total_marks']:g}")
            data.append(row)
        data.append(['', '', 'Subject mean'] + [f"{subject_means.get(sub, 0):g}" for sub in subjects] + [''])

        col_widths = [32, 55, 130] + [56] * len(subjects) + [50]
        table = Table(data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10002b')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (3, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#999999')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f5ecff')]),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e0c3fc')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("Levels: EE 90 and above, ME 70-89, AE 40-69, BE below 40.", styles['Normal']))

        doc.build(elements)

        filename = f"{class_name}_{term}_Class_Report.pdf".replace(' ', '_')
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
class ClassListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Resolve the Classroom model from StudentProfile.classroom so no import name is guessed
        Classroom = StudentProfile._meta.get_field('classroom').related_model
        data = [{"id": c.id, "name": c.name} for c in Classroom.objects.all().order_by('name')]
        return Response(data)

