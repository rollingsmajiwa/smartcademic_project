from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('parent', 'Parent'),
        ('admin', 'Admin'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    # False for newly invited student/teacher/parent accounts until admin updates/approves them.
    # Default True so existing accounts are not disrupted after migrating.
    is_admin_approved = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


# ---------------------------------------------------------------------------
# Keep UserProfile.role (the source of truth) and the staff flag in sync
# whenever a teacher, student, or parent record is saved, from anywhere: the
# admin dashboard endpoints, /admin, the invite flow, or the shell.
#
# String senders ("app_label.Model") avoid importing admin_app here, so there
# is no circular import.
# ---------------------------------------------------------------------------
def _sync_role(user, role):
    profile, created = UserProfile.objects.get_or_create(user=user, defaults={'role': role})

    # Fixes profiles created with the model default ('student') for non-student roles.
    if not created and profile.role not in (role, 'admin'):
        profile.role = role
        profile.save(update_fields=['role'])

    # Only admins keep access to the Django admin site.
    if profile.role != 'admin' and user.is_staff and not user.is_superuser:
        user.is_staff = False
        user.save(update_fields=['is_staff'])


@receiver(post_save, sender='admin_app.TeacherProfile')
def teacher_profile_saved(sender, instance, **kwargs):
    _sync_role(instance.user, 'teacher')


@receiver(post_save, sender='admin_app.StudentProfile')
def student_profile_saved(sender, instance, **kwargs):
    _sync_role(instance.user, 'student')


@receiver(post_save, sender='admin_app.ParentProfile')
def parent_profile_saved(sender, instance, **kwargs):
    _sync_role(instance.user, 'parent')