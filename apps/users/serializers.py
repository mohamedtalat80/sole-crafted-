"""
Serializers for the users app.

Design (SRP):
- Each serializer handles exactly one request/response shape.
- No business logic here — that belongs in UserService.
- Input serializers validate data; output serializers represent resources.
"""
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema_field, extend_schema_serializer
from rest_framework import serializers

from apps.core.serializers import ChoiceField, StrictModelSerializer, StrictSerializer
from apps.users.models import CustomUser


# ---------------------------------------------------------------------------
# Output / Resource serializer
# ---------------------------------------------------------------------------

class UserProfileSerializer(StrictModelSerializer):
    """Read-only representation of a user returned in auth responses."""

    notification_ids = serializers.SerializerMethodField()
    specific_data = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "full_name",
            "email",
            "phone_number",
            "profile_image",
            "notification_ids",
            "is_verified",
            "is_banned",
            "nationality",
            "address",
            "account_type",
            "specific_data",
        ]
        read_only_fields = fields

    def get_notification_ids(self, obj) -> list[str]:
        return list(obj.devices.order_by("-created_at").values_list("fcm_token", flat=True))

    def get_specific_data(self, obj) -> dict | None:
        if obj.account_type == CustomUser.AccountType.CUSTOMER:
            return {
                "date_of_birth": obj.date_of_birth,
                "gender": obj.gender,
            }

    def _file_url(self, field) -> str | None:
        if not field:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(field.url)
        return field.url


# ---------------------------------------------------------------------------
# Auth input serializers
# ---------------------------------------------------------------------------

@extend_schema_serializer(component_name="SignUp")
class SignUpSerializer(StrictSerializer):
    """Validates the signup request body."""

    full_name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    notifications_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate_password(self, value: str) -> str:
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        return value


class LoginSerializer(StrictSerializer):
    """Validates the login request body."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    notifications_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class RefreshTokenSerializer(StrictSerializer):
    """Used only for Swagger documentation of the refresh endpoint."""

    refresh = serializers.CharField()


class LogoutSerializer(StrictSerializer):
    """Validates the logout request body."""

    refresh = serializers.CharField()


# ---------------------------------------------------------------------------
# Social login serializer
# ---------------------------------------------------------------------------

@extend_schema_serializer(component_name="SocialLogin")
class SocialLoginSerializer(StrictSerializer):
    """
    Validates the social login request body.

    The mobile app sends:
      - provider:     which social provider ("google" or "apple")
      - id_token: the ID token received from the provider's SDK
      - account_type: what type of account to create if user is new
      - notifications_id: optional FCM token for push notifications
    """

    provider = ChoiceField(choices=["google", "apple"])
    # Capped at 5000 chars to prevent memory abuse — real tokens are < 3000 chars
    id_token = serializers.CharField(max_length=5000, min_length=10)
    notifications_id = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        allow_null=True,
    )


# ---------------------------------------------------------------------------
# Profile update serializer
# ---------------------------------------------------------------------------

class UpdateProfileSerializer(StrictModelSerializer):
    """Partial update of a user's profile."""

    class Meta:
        model = CustomUser
        fields = [
            "full_name",
            "phone_number",
            "profile_image",
            "date_of_birth",
            "gender",
            "address",
            "nationality",
        ]

    def validate_phone_number(self, value: str) -> str:
        if value and not value.startswith("+"):
            raise serializers.ValidationError("Phone number must be in international format (e.g. +201234567890).")
        return value


# ---------------------------------------------------------------------------
# Email verification serializers
# ---------------------------------------------------------------------------

class SendVerificationCodeSerializer(StrictSerializer):
    """Validates the send-verification-code request body."""
    email = serializers.EmailField()


class VerifyEmailCodeSerializer(StrictSerializer):
    """Validates the verify-email-code request body."""
    email = serializers.EmailField()
    verification_code = serializers.CharField(min_length=6, max_length=6)


# ---------------------------------------------------------------------------
# Password reset serializers
# ---------------------------------------------------------------------------

class ForgotPasswordSerializer(StrictSerializer):
    email = serializers.EmailField()


class VerifyResetCodeSerializer(StrictSerializer):
    email = serializers.EmailField()
    code = serializers.CharField(min_length=6, max_length=6)


class SetNewPasswordSerializer(StrictSerializer):
    """Step 3 of forgot-password flow: set a new password using the verified code."""
    email = serializers.EmailField()
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_new_password(self, value: str) -> str:
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        return value


class ResetPasswordSerializer(StrictSerializer):
    email = serializers.EmailField()
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_new_password(self, value: str) -> str:
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        return value


# ---------------------------------------------------------------------------
# Password confirmation serializer (account delete / deactivate)
# ---------------------------------------------------------------------------

class PasswordConfirmSerializer(StrictSerializer):
    """Used when an action requires the user to re-enter their password."""
    password = serializers.CharField(write_only=True)


# ---------------------------------------------------------------------------
# Change email serializer
# ---------------------------------------------------------------------------

class ChangePasswordSerializer(StrictSerializer):
    """Change password for an authenticated user (JWT token required in header)."""
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_new_password(self, value: str) -> str:
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        return value


class ChangeEmailSerializer(StrictSerializer):
    """Change email for an authenticated user (JWT token required in header)."""
    new_email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


# ---------------------------------------------------------------------------
# OTP-based email change serializers (2-step flow)
# ---------------------------------------------------------------------------

class RequestChangeEmailSerializer(StrictSerializer):
    """Step 1 — validate password and dispatch OTP to the new email address."""
    new_email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class VerifyChangeEmailSerializer(StrictSerializer):
    """Step 2 — confirm OTP and apply the new email address."""
    new_email = serializers.EmailField()
    code = serializers.CharField(min_length=6, max_length=6)


# ---------------------------------------------------------------------------
# FCM token update serializer
# ---------------------------------------------------------------------------

class SetFcmTokenSerializer(StrictSerializer):
    """Validates the set-fcm-token request body."""
    # FCM tokens are ~200 chars; cap at 500 for safety
    fcm_token = serializers.CharField(max_length=500, min_length=10)
