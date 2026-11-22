from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import AccessCode, Device, User, normalize_phone


class PhoneField(serializers.CharField):
    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        try:
            return normalize_phone(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages[0]) from exc


class LanguageField(serializers.ChoiceField):
    """Ilova tili. Olib tashlangan `qq` (eski ilova yuboradi) — `uz` deb olinadi."""

    LEGACY = {"qq": User.Language.UZ}

    def __init__(self, **kwargs):
        super().__init__(choices=User.Language.choices, **kwargs)

    def to_internal_value(self, data):
        return super().to_internal_value(self.LEGACY.get(data, data))


def tokens_for(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


SESSION_CLAIM = "did"


def issue_tokens(user: User, platform: str = "", label: str = "",
                 not_after=None, unlimited: bool = False, machine_id: str = "",
                 guest: bool = False) -> dict:
    """JWT chiqaradi va sessiyani `Device` ga yozadi.

    `not_after` berilsa sessiya muddati undan oshmaydi.
    Limit to'lgan bo'lsa `devices.DeviceLimitReached` ko'tariladi;
    `unlimited=True` — qurilma limiti ham, sessiya muddati ham yo'q (kirish kodi).
    `guest=True` — mehmon sessiyasi (`settings.GUEST_DAYS` kun).
    """
    from .devices import register_device, register_guest_device

    refresh = RefreshToken.for_user(user)
    if guest:
        device = register_guest_device(user, refresh, label, machine_id)
    else:
        device = register_device(user, platform, label, refresh, not_after=not_after,
                                 unlimited=unlimited, machine_id=machine_id)
    if machine_id or guest:
        # Kod sessiyasi: har so'rovda `Device` tirikligi tekshiriladi
        # (`common.authentication`). Claim refresh rotatsiyasida ham saqlanadi.
        refresh[SESSION_CLAIM] = device.pk
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ("id", "platform", "label", "created_at", "last_seen", "expires_at")


def pro_tier(user) -> int | None:
    """Profil rangi uchun PRO darajasi: 1 — 15 kun, 2 — 1 oy, 3 — 3 oy (PRO'siz — None).

    Oxirgi to'langan buyurtma tarifidan; admin bergan PRO uchun qolgan kunlardan,
    muddatsiz PRO — eng yuqori daraja.
    """
    if not user.pro_active:
        return None
    from apps.payments.models import ProOrder

    days = (ProOrder.objects.filter(user=user, status=ProOrder.Status.PAID)
            .order_by("-paid_at", "-pk").values_list("days", flat=True).first())
    if days is None:
        if user.pro_until is None:
            return 3
        days = (user.pro_until - timezone.now()).days + 1
    return 1 if days <= 15 else 2 if days <= 31 else 3


DEFAULT_TIER_COLORS = {1: "#2F80ED", 2: "#8E44AD", 3: "#E0A100"}


def pro_color(user) -> str | None:
    """Profil halqasi rangi — tarifning admin'da tanlangan rangi (PRO'siz — None).

    Oxirgi to'langan buyurtma tarifidan; admin bergan PRO uchun qolgan kunlarga
    eng yaqin tarifdan (eng kichik `days >= qolgan`, bo'lmasa eng uzun tarif).
    """
    if not user.pro_active:
        return None
    from apps.payments.models import ProOrder, ProPlan

    order = (ProOrder.objects.filter(user=user, status=ProOrder.Status.PAID, plan__isnull=False)
             .select_related("plan").order_by("-paid_at", "-pk").first())
    if order is not None:
        return order.plan.color
    plans = ProPlan.objects.filter(is_active=True).order_by("days")
    if not plans:
        return DEFAULT_TIER_COLORS[pro_tier(user)]
    if user.pro_until is None:
        return plans.last().color
    left = (user.pro_until - timezone.now()).days + 1
    plan = plans.filter(days__gte=left).first() or plans.last()
    return plan.color


class UserSerializer(serializers.ModelSerializer):
    language = LanguageField(required=False)
    initials = serializers.CharField(read_only=True)
    pro_active = serializers.BooleanField(read_only=True)
    pro_tier = serializers.SerializerMethodField()
    pro_color = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id", "phone", "full_name", "role", "language", "dark_theme",
            "is_pro", "pro_until", "pro_active", "pro_tier", "pro_color", "initials", "date_joined",
        )
        # Rolni foydalanuvchi o'zi o'zgartira olmaydi — faqat shef (manage/users/).
        read_only_fields = ("id", "phone", "role", "is_pro", "pro_until", "date_joined")

    def get_pro_tier(self, obj) -> int | None:
        return pro_tier(obj)

    def get_pro_color(self, obj) -> str | None:
        return pro_color(obj)


def guest_from_refresh(raw: str) -> User | None:
    """Mehmonni refresh tokeni orqali topadi (imzo va 90 kunlik umri tekshiriladi).

    Mehmon sessiyasining 3 kunlik muddati bu yerda ahamiyatsiz — muddati
    tugagan mehmon ham ro'yxatdan o'tib aylana oladi.
    """
    if not raw:
        return None
    try:
        payload = RefreshToken(raw).payload
    except TokenError:
        return None
    return User.objects.filter(
        pk=payload.get("user_id"), role=User.Role.GUEST, is_active=True
    ).first()


class GuestSerializer(serializers.Serializer):
    # Ilova o'rnatilganda yaratadigan tasodifiy ID — faqat ma'lumot uchun.
    device_id = serializers.CharField(max_length=64)
    lang = LanguageField(required=False, default=User.Language.UZ)
    device_label = serializers.CharField(max_length=120, required=False, allow_blank=True)


class AccessCodeLoginSerializer(serializers.Serializer):
    """Kod bilan kirish — desktop darslik va imtihon uchun."""

    code = serializers.CharField(max_length=16)
    platform = serializers.CharField(max_length=10, required=False, allow_blank=True)
    device_label = serializers.CharField(max_length=120, required=False, allow_blank=True)
    # Kompyuter ID'si (desktop: MachineGuid xeshi, web: brauzer uchun tasodifiy).
    # Majburiy emas — yo'qligini view aniq xabar bilan rad etadi.
    device_id = serializers.CharField(max_length=64, required=False, allow_blank=True)

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
    is_bound = serializers.BooleanField(read_only=True)

    class Meta:
        model = AccessCode
        fields = (
            "id", "code", "user", "created_by", "valid_days",
            "created_at", "activated_at", "expires_at", "is_active",
            "is_bound", "bound_at",
        )
        # `device_id` ataylab chiqarilmaydi — shefga faqat biriktirilganmi yo'qmi kerak.
        read_only_fields = (
            "id", "code", "created_by", "created_at", "activated_at", "expires_at",
            "is_bound", "bound_at",
        )
        extra_kwargs = {"valid_days": {"required": False}}
