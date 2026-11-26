import logging
import re

import requests
from django.conf import settings

from admin_app.models import ParentProfile
from parents_app.permissions import get_linked_children, resolve_child_for_parent
from parents_app.serializers import (
    ParentAssignmentSubmissionSerializer,
    ParentExamSubmissionSerializer,
    ParentStudentMarkSerializer,
    normalize_phone_number,
)
from student_app.models import AssignmentSubmission, ExamSubmission
from teachers_app.models import StudentMark

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = getattr(settings, "WHATSAPP_GRAPH_API_VERSION", "v21.0")


def find_parent_by_phone(raw_phone):
    normalized = normalize_phone_number(raw_phone)
    if not normalized:
        return None
    return (
        ParentProfile.objects.select_related("user")
        .prefetch_related("children__user", "children__classroom")
        .filter(phone_number=normalized)
        .first()
    )


def _match_child_from_text(children, text_lower):
    for child in children:
        adm = (child.admission_number or "").strip().lower()
        full_name = (child.user.get_full_name() or "").strip().lower()
        first_name = (child.user.first_name or "").strip().lower()
        if adm and adm in text_lower:
            return child
        if full_name and full_name in text_lower:
            return child
        if first_name and len(first_name) >= 2 and re.search(rf"\b{re.escape(first_name)}\b", text_lower):
            return child
    return None


def _format_report_card_text(child, report_data):
    child_name = child.user.get_full_name().strip() or child.admission_number
    subjects = report_data.get("subjects") or []
    summary = report_data.get("summary") or {}

    if not subjects:
        return (
            f"*{child_name}* ({child.admission_number})\n"
            f"No report card marks found for {report_data.get('term')} {report_data.get('year')}."
        )

    lines = [
        f"*Report Card — {child_name}* ({child.admission_number})",
        f"Term: {report_data.get('term')} ({report_data.get('year')})",
        "",
    ]
    for row in subjects[:12]:
        lines.append(f"• {row.get('subject')}: *{row.get('marks')}*")

    lines.extend([
        "",
        f"Subjects: {summary.get('subject_count', len(subjects))}",
        f"Total: {summary.get('total_marks', '-')} | Avg: {summary.get('average_marks', '-')}",
    ])
    return "\n".join(lines)


def _format_marks_text(child, marks_qs):
    child_name = child.user.get_full_name().strip() or child.admission_number
    items = ParentStudentMarkSerializer(marks_qs[:15], many=True).data
    if not items:
        return f"*{child_name}* ({child.admission_number})\nNo mark entries found."

    lines = [f"*Recent Marks — {child_name}* ({child.admission_number})", ""]
    for item in items:
        lines.append(
            f"• {item['subject']} ({item['exam_type']}, {item['term']} {item['year']}): *{item['marks']}*"
        )
    return "\n".join(lines)


def _format_submissions_text(child):
    child_name = child.user.get_full_name().strip() or child.admission_number
    assignments = ParentAssignmentSubmissionSerializer(
        AssignmentSubmission.objects.filter(student=child.user)
        .select_related("assignment")
        .order_by("-submitted_at")[:8],
        many=True,
    ).data
    exams = ParentExamSubmissionSerializer(
        ExamSubmission.objects.filter(student=child.user)
        .select_related("exam")
        .order_by("-submitted_at")[:8],
        many=True,
    ).data

    lines = [
        f"*Submissions & Feedback — {child_name}* ({child.admission_number})",
        "",
        "*Assignments:*",
    ]
    if not assignments:
        lines.append("• None recorded.")
    else:
        for a in assignments:
            grade = a.get("grade") if a.get("grade") is not None else "Pending"
            fb = f" — {a['feedback']}" if a.get("feedback") else ""
            lines.append(f"• {a['assignment_title']}: *{grade}*{fb}")

    lines.extend(["", "*Exams:*"])
    if not exams:
        lines.append("• None recorded.")
    else:
        for ex in exams:
            score = ex.get("score") if ex.get("score") is not None else "-"
            fb = f" — {ex['feedback']}" if ex.get("feedback") else ""
            lines.append(f"• {ex['exam_title']} ({ex['status']}): *{score}*{fb}")

    return "\n".join(lines)


def build_whatsapp_reply(sender_phone, message_text):
    from parents_app.views import build_report_card_data

    parent = find_parent_by_phone(sender_phone)
    if not parent:
        return (
            "Your WhatsApp number is not linked to a SmartAcademic parent account yet. "
            "Please sign in to the Parent Portal, open *Edit Name & WhatsApp*, and save your number."
        )

    children = list(get_linked_children(parent.user))
    if not children:
        return (
            f"Hello {parent.user.get_full_name().strip() or parent.user.username}, "
            "no learners are linked to your parent account yet. Please contact school administration."
        )

    text = (message_text or "").strip()
    lower = text.lower()

    if lower in {"", "hi", "hello", "menu", "help", "start"}:
        child_list = "\n".join(
            f"• {c.user.get_full_name().strip() or c.user.username} ({c.admission_number})"
            for c in children
        )
        return (
            f"Hello {parent.user.get_full_name().strip() or parent.user.username}! Linked learner(s):\n"
            f"{child_list}\n\n"
            "Reply with:\n"
            "• *report* — latest report card\n"
            "• *marks* — exam & term marks\n"
            "• *submissions* — assignments & feedback\n"
            "(Optional: include learner name or admission number, e.g. *report 001*)"
        )

    matched_child = _match_child_from_text(children, lower)
    target_child = resolve_child_for_parent(
        parent.user,
        student_id=matched_child.id if matched_child else children[0].id,
    )

    if any(word in lower for word in ("sub", "assign", "work", "feedback")):
        return _format_submissions_text(target_child)

    if "mark" in lower or "exam" in lower or "score" in lower:
        marks_qs = StudentMark.objects.filter(student=target_child).order_by("-year", "-id")
        return _format_marks_text(target_child, marks_qs)

    report_data = build_report_card_data(target_child)
    return _format_report_card_text(target_child, report_data)


def send_whatsapp_text(recipient_phone, body_text):
    token = getattr(settings, "WHATSAPP_ACCESS_TOKEN", "")
    phone_number_id = getattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "")
    normalized_to = normalize_phone_number(recipient_phone)

    if not token or not phone_number_id:
        logger.info(
            "WhatsApp outbound skipped (missing token/phone_number_id). Reply:\n%s",
            body_text,
        )
        return {"sent": False, "reason": "missing_credentials", "reply": body_text}

    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": normalized_to,
        "type": "text",
        "text": {"body": body_text[:4096]},
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    resp = requests.post(url, json=payload, headers=headers, timeout=15)
    resp.raise_for_status()
    return {"sent": True, "response": resp.json()}