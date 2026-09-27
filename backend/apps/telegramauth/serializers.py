from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.accounts.models import normalize_phone

from .models import Purpose


class PhoneField(serializers.CharField):
    """apps.accounts bilan bir xil normalizatsiya (9 xonali -> +998...)."""

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        try:
            return normalize_phone(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages[0]) from exc


class SendCodeSerializer(serializers.Serializer):
    phone = PhoneField(max_length=20)
    purpose = serializers.ChoiceField(choices=Purpose.choices, default=Purpose.RESET)


class VerifyCodeSerializer(serializers.Serializer):
    phone = PhoneField(max_length=20)
    purpose = serializers.ChoiceField(choices=Purpose.choices, default=Purpose.RESET)
    code = serializers.CharField(max_length=6, min_length=6)


class ResetPasswordSerializer(serializers.Serializer):
    phone = PhoneField(max_length=20)
    token = serializers.CharField(max_length=64)
    password = serializers.CharField(write_only=True, min_length=6)
