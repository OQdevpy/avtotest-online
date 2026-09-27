from datetime import timedelta

from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import SocialAccount, User, normalize_phone


class PhoneField(serializers.CharField):
    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        try:
            return normalize_phone(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages[0]) from exc


def tokens_for(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class UserSerializer(serializers.ModelSerializer):
    initials = serializers.CharField(read_only=True)
    pro_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id", "phone", "full_name", "language", "dark_theme",
            "is_pro", "pro_until", "pro_active", "initials", "date_joined",
        )
        read_only_fields = ("id", "phone", "is_pro", "pro_until", "date_joined")


class RegisterSerializer(serializers.Serializer):
    phone = PhoneField(max_length=20)
    password = serializers.CharField(write_only=True, min_length=6)
    full_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    language = serializers.ChoiceField(
        choices=User.Language.choices, required=False, default=User.Language.UZ
    )

    def validate_phone(self, value: str) -> str:
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("Bu raqam allaqachon ro'yxatdan o'tgan.")
        return value

    def create(self, validated):
        user = User.objects.create_user(**validated)
        user.is_pro = True
        user.pro_until = timezone.now() + timedelta(days=12)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    phone = PhoneField(max_length=20)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs["phone"], password=attrs["password"])
        if user is None:
            raise serializers.ValidationError("Telefon raqam yoki parol noto'g'ri.")
        if not user.is_active:
            raise serializers.ValidationError("Hisob bloklangan.")
        attrs["user"] = user
        return attrs


class SocialLoginSerializer(serializers.Serializer):
    """Signs a user in via an external provider.

    `uid` must already be verified against the provider by the caller/view —
    see the TODO in `views.SocialLoginView`.
    """

    provider = serializers.ChoiceField(choices=SocialAccount.Provider.choices)
    uid = serializers.CharField(max_length=191)
    email = serializers.EmailField(required=False, allow_blank=True)
    full_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    phone = PhoneField(max_length=20, required=False)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=6)

    def validate_old_password(self, value: str) -> str:
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Joriy parol noto'g'ri.")
        return value
