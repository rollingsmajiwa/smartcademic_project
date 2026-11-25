from rest_framework import permissions
from rest_framework.exceptions import NotFound, PermissionDenied

from accounts.views import ADMIN, PARENT, get_user_role
from admin_app.models import StudentProfile


class IsParentReadOnly(permissions.BasePermission):
    """Parents get read-only access to their own linked children."""

    message = "Only parent accounts can access this read-only portal."

    def has_permission(self, request, view):
        if request.method not in permissions.SAFE_METHODS:
            return False
        user = request.user
        if not (user and user.is_authenticated and user.is_active):
            return False
        return get_user_role(user) == PARENT or hasattr(user, "parent_profile")


class IsAdminUserOrStaff(permissions.BasePermission):
    """
    Admins only (superuser or UserProfile.role == "admin), using the same
    get_user_role() the rest of the project uses.

    is_staff is deliberately NOT accepted on its own: the teacher serializer
    sets is_staff=True on teachers, so accepting it would let teachers
    manage parent links.
    """

    message = "Only admin accounts can manage parent-child links."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.is_active):
            return False
        return get_user_role(user) == ADMIN


def get_linked_children(user):
    parent_profile = getattr(user, "parent_profile", None)
    if not parent_profile:
        return StudentProfile.objects.none()
    return parent_profile.children.select_related("user", "classroom").order_by(
        "user__first_name", "admission_number"
    )


def resolve_child_for_parent(user, student_id=None):
    """
    Returns the StudentProfile to display.
    Returns None when several children are linked and no student_id was given.
    """
    children = get_linked_children(user)
    if not children.exists():
        raise PermissionDenied("No students are linked to this parent account.")

    if student_id is not None and str(student_id).strip() != "":
        try:
            parsed_id = int(student_id)
        except (TypeError, ValueError):
            raise NotFound("Invalid student_id parameter.")
        child = children.filter(id=parsed_id).first()
        if not child:
            raise PermissionDenied("You do not have access to this student's records.")
        return child

    if children.count() == 1:
        return children.first()
    return None