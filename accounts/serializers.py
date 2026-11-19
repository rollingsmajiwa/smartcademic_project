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
    """Used by admins to list, create, and update users with role & approval state."""

    role = serializers.ChoiceField(choices=UserProfile.ROLE_CHOICES, source='profile.role')
    is_admin_approved = serializers.BooleanField(
        source='profile.is_admin_approved',
        required=False,
    )
    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        style={'input_type': 'password'},
    )

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'is_active',
            'password',
            'role',
            'is_admin_approved',
        )
        read_only_fields = ('id',)

    def validate_email(self, value):
        value = value.strip().lower()
        if value:
            qs = User.objects.filter(email__iexact=value)
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError('A user with this email already exists.')
        return value

    def validate_password(self, value):
        if not value:
            return value
        try:
            run_password_validators(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value

    def validate(self, attrs):
        profile_data = attrs.get('profile') or {}
        role = profile_data.get('role')
        request = self.context.get('request')

        if self.instance is None and not attrs.get('password'):
            raise serializers.ValidationError({'password': 'Password is required when creating a user.'})

        if role == 'admin' and not (request and request.user.is_superuser):
            raise serializers.ValidationError({'role': 'Only superusers can assign the admin role.'})

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        from .views import attach_role_profiles

        profile_data = validated_data.pop('profile', {})
        role = profile_data.get('role', 'student')
        approved = profile_data.get('is_admin_approved', True)

        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            password=validated_data['password'],
        )
        attach_role_profiles(user, role, is_admin_approved=approved)
        return user

    @transaction.atomic
    def update(self, instance, validated_data):
        from .views import attach_role_profiles

        profile_data = validated_data.pop('profile', {})
        password = validated_data.pop('password', None)

        for attr, val in validated_data.items():
            setattr(instance, attr, val)

        if password:
            instance.set_password(password)

        instance.save()

        profile, _ = UserProfile.objects.get_or_create(user=instance)
        role = profile_data.get('role', profile.role)
        attach_role_profiles(instance, role)

        # Updating a learner or teacher by an admin marks them reviewed/approved
        # unless explicitly passed as False.
        if 'is_admin_approved' in profile_data:
            profile.is_admin_approved = profile_data['is_admin_approved']
        else:
            profile.is_admin_approved = True
        profile.save(update_fields=['is_admin_approved'])

        return instance