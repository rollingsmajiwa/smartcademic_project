from django.contrib import admin

from admin_app.models import ParentProfile


@admin.register(ParentProfile)
class ParentProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "phone_number", "children_count", "created_at")
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "phone_number",
        "children__admission_number",
    )
    filter_horizontal = ("children",)

    def children_count(self, obj):
        return obj.children.count()

    children_count.short_description = "Linked Children"