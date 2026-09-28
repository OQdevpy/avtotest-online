from datetime import timedelta

from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import AccessCode, Device, SocialAccount, User, normalize_phone


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


def issue_tokens(user: User, platform: str = "", label: str = "",
                 not_after=None, unlimited: bool = False) -> dict:
    """JWT chiqaradi va sessiyani `Device` ga yozadi.

    `not_after` berilsa sessiya muddati undan oshmaydi.
    Limit to'lgan bo'lsa `devices.DeviceLimitReached` ko'tariladi;
    `unlimited=True` — qurilma limiti ham, sessiya muddati ham yo'q (kirish kodi).
    """
    from .devices import register_device

    refresh = RefreshToken.for_user(user)
    register_device(user, platform, label, refresh, not_after=not_after,
                    unlimited=unlimited)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ("id", "platform", "label", "created_at", "last_seen", "expires_at")


class UserSerializer(serializers.ModelSerializer):
    initials = serializers.CharField(read_only=True)
    pro_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id", "phone", "full_name", "role", "language", "dark_theme",
            "is_pro", "pro_until", "pro_active", "initials", "date_joined",
        )
        # Rolni foydalanuvchi o'zi o'zgartira olmaydi — faqat shef (manage/users/).
        read_only_fields = ("id", "phone", "role", "is_pro", "pro_until", "date_joined")


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
        phone, password = attrs["phone"], attrs["password"]

        # Talaba (Student) bo'lsa — mobil kirish ochiq PIN bilan tekshiriladi,
        # front-ofisda berilgan PIN har doim ishlashi kerak. Aks holda odatdagi
        # hash orqali tekshiriladi (o'qituvchi/shef yoki ilovada ro'yxatdan
        # o'tgan foydalanuvchi).
        from apps.billing.models import Student

        student = Student.objects.filter(phone=phone).select_related("user").first()
        if student is not None:
            if student.password != password:
                raise serializers.ValidationError("Telefon raqam yoki parol noto'g'ri.")
            user = student.user
            if user is None or not student.is_active or not user.is_active:
                raise serializers.ValidationError("Hisob bloklangan.")
        else:
            user = authenticate(username=phone, password=password)
            if user is None:
                raise serializers.ValidationError("Telefon raqam yoki parol noto'g'ri.")
            if not user.is_active:
                raise serializers.ValidationError("Hisob bloklangan.")

        attrs["user"] = user
        return attrs


class SocialLoginSerializer(serializers.Serializer):
    """Tashqi provayder orqali kirish.

    `token` majburiy — `views.SocialLoginView` uni provayderda tekshiradi va
    `uid` ni tasdiqlangan qiymat bilan almashtiradi.
    """

    provider = serializers.ChoiceField(choices=SocialAccount.Provider.choices)
    token = serializers.CharField()
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


class AccessCodeLoginSerializer(serializers.Serializer):
    """Kod bilan kirish — desktop darslik va imtihon uchun."""

    code = serializers.CharField(max_length=16)
    platform = serializers.CharField(max_length=10, required=False, allow_blank=True)
    device_label = serializers.CharField(max_length=120, required=False, allow_blank=True)

    def validate_code(self, value: str) -> str:
        code = (
            AccessCode.objects.select_related("user")
            .filter(code=value.strip().upper())
            .first()
        )
        # Kod muddatsiz va ko'p martalik: topilsa bo'ldi. Faqat shef o'chirgan
        # (is_active=False) kod yoki bloklangan foydalanuvchi rad etiladi.
        if code is None or not code.is_active or not code.user.is_active:
            raise serializers.ValidationError("Kod yaroqsiz yoki muddati tugagan.")
        self.context["access_code"] = code
        return value


class AccessCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessCode
        fields = (
            "id", "code", "user", "created_by", "valid_days",
            "created_at", "activated_at", "expires_at", "is_active",
        )
        read_only_fields = (
            "id", "code", "created_by", "created_at", "activated_at", "expires_at",
        )
        extra_kwargs = {"valid_days": {"required": False}}
