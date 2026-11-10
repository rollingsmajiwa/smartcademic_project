from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password as run_password_validators
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import UserProfile


# NOTE: The views module imports this one, so anything we need from views.py
# is imported lazily inside the methods below to avoid a circular import.


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Embeds the user's role in the JWT, using the same logic as the views."""

    @classmethod
    def get_token(cls, user):
        from .views import get_user_role

        token = super().get_token(user)
        token['role'] = get_user_role(user)
        token['username'] = user.username
        return token


class AdminUserManagementSerializer(serializers.ModelSerializer):
    """Used by admins to list users and to create them with a given role."""

    role = serializers.ChoiceField(choices=UserProfile.ROLE_CHOICES, source='profile.role')
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'role')

    def validate_email(self, value):
        value = value.strip().lower()
        if value and User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value

    def validate_password(self, value):
        try:
            run_password_validators(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value

    def validate(self, attrs):
        role = attrs.get('profile', {}).get('role')
        request = self.context.get('request')
        if role == 'admin' and not (request and request.user.is_superuser):
            raise serializers.ValidationError({'role': 'Only superusers can create admins.'})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        from .views import attach_role_profiles

        role = validated_data.pop('profile')['role']
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
        )
        # Creates UserProfile, the teacher/student profile, and sets the
        # staff flag correctly for the role.
        attach_role_profiles(user, role)
        return user