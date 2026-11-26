from rest_framework import serializers

from admin_app.models import ParentProfile, StudentProfile
from student_app.models import AssignmentSubmission, ExamSubmission
from teachers_app.models import StudentMark


class ParentStudentMarkSerializer(serializers.ModelSerializer):
    subject_code = serializers.CharField(source="subject", read_only=True)
    subject = serializers.CharField(source="get_subject_display", read_only=True)

    class Meta:
        model = StudentMark
        fields = [
            "id",
            "subject_code",
            "subject",
            "marks",
            "term",
            "year",
            "exam_type",
            "class_name",
            "updated_at",
        ]


class ParentChildSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    classroom_name = serializers.SerializerMethodField()

    class Meta:
        model = StudentProfile
        fields = [
            "id",
            "user_id",
            "username",
            "full_name",
            "admission_number",
            "classroom_name",
            "gender",
        ]

    def get_full_name(self, obj):
        parts = [obj.user.first_name, obj.surname, obj.user.last_name]
        name = " ".join(part.strip() for part in parts if part and part.strip())
        return name or obj.user.username

    def get_classroom_name(self, obj):
        return obj.classroom.name if obj.classroom else None


class ParentAssignmentSubmissionSerializer(serializers.ModelSerializer):
    assignment_title = serializers.CharField(source="assignment.title", read_only=True)
    feedback = serializers.CharField(source="grade_description", read_only=True, allow_null=True)

    class Meta:
        model = AssignmentSubmission
        fields = [
            "id",
            "assignment_id",
            "assignment_title",
            "submitted_at",
            "grade",
            "feedback",
        ]


class ParentExamSubmissionSerializer(serializers.ModelSerializer):
    exam_title = serializers.CharField(source="exam.title", read_only=True)
    feedback = serializers.CharField(source="grade_description", read_only=True, allow_null=True)

    class Meta:
        model = ExamSubmission
        fields = [
            "id",
            "exam_id",
            "exam_title",
            "submitted_at",
            "score",
            "status",
            "feedback",
        ]


class ParentProfileDetailSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    full_name = serializers.CharField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    children = ParentChildSerializer(many=True, read_only=True)

    class Meta:
        model = ParentProfile
        fields = [
            "id",
            "username",
            "email",
            "full_name",
            "phone_number",
            "children",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["full_name"] = instance.user.get_full_name().strip() or instance.user.username
        return data

    def validate_phone_number(self, value):
        return normalize_phone_number(value)

    def update(self, instance, validated_data):
        full_name = validated_data.pop("full_name", None)
        if full_name is not None:
            cleaned = " ".join(full_name.strip().split())
            parts = cleaned.split(" ", 1)
            instance.user.first_name = parts[0] if parts and parts[0] else ""
            instance.user.last_name = parts[1] if len(parts) > 1 else ""
            instance.user.save(update_fields=["first_name", "last_name"])

        if "phone_number" in validated_data:
            instance.phone_number = normalize_phone_number(validated_data["phone_number"])

        return super().update(instance, validated_data)