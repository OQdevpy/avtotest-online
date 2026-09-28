"""Qurilma sessiyalari — limit va muddat.

Limit platformaga qarab (`settings.MAX_DEVICES_PER_PLATFORM`); `User.max_devices`
to'ldirilgan bo'lsa u barcha platformalar uchun ustun turadi. Muddat ham
platformaga qarab (`settings.SESSION_DAYS`); `None` — muddat yo'q, refresh
tokenning o'z umri amal qiladi.
"""

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import Device


class DeviceLimitReached(Exception):
    """Shu platformada ruxsat etilgan qurilma soni to'lgan."""


def _limit(user, platform: str) -> int:
    if user.max_devices is not None:
        return user.max_devices
    return settings.MAX_DEVICES_PER_PLATFORM.get(platform, 1)


def _expiry(platform: str):
    days = settings.SESSION_DAYS.get(platform)
    return None if days is None else timezone.now() + timedelta(days=days)


def active_devices(user, platform: str):
    """Muddati o'tganlarni yo'lda `is_active=False` qilib, faollarni qaytaradi."""
    stale = Device.objects.filter(
        user=user, platform=platform, is_active=True,
        expires_at__isnull=False, expires_at__lte=timezone.now(),
    )
    if stale.exists():
        stale.update(is_active=False)
    return Device.objects.filter(user=user, platform=platform, is_active=True)


@transaction.atomic
def register_device(user, platform: str, label: str, refresh, not_after=None) -> Device:
    """Yangi sessiya yozadi. Limit to'lgan bo'lsa `DeviceLimitReached`, faqat
    `settings.DEVICE_EVICT_OLDEST` dagi platformalarda eng eski sessiya yopiladi.

    Foydalanuvchi qatori qulflanadi: aks holda bir vaqtda kelgan ikki kirish
    ikkisi ham bo'sh joy ko'rib, bitta qurilmalik tarifni chetlab o'tardi.
    `not_after` — sessiya muddatining yuqori chegarasi (kirish kodi uchun).
    """
    platform = platform or Device.Platform.MOBILE
    type(user).objects.select_for_update().filter(pk=user.pk).first()
    active = active_devices(user, platform)
    overflow = active.count() - _limit(user, platform) + 1
    if overflow > 0:
        if platform not in settings.DEVICE_EVICT_OLDEST:
            raise DeviceLimitReached
        # Mobil ilova chiqishda serverga xabar bermaydi — slot bo'shamaydi.
        # 403 o'rniga eng uzoq ishlatilmagan sessiyalar yopiladi.
        oldest = active.order_by("last_seen", "pk").values_list("pk", flat=True)[:overflow]
        Device.objects.filter(pk__in=list(oldest)).update(is_active=False)

    expires_at = _expiry(platform)
    if not_after is not None:
        expires_at = min(expires_at, not_after) if expires_at else not_after
    return Device.objects.create(
        user=user,
        platform=platform,
        refresh_jti=refresh["jti"],
        label=label or "",
        expires_at=expires_at,
    )


def device_for_refresh(jti: str) -> tuple[Device | None, str]:
    """Refresh uchun yaroqli qurilma va sabab.

    Sabab `"ok"`, `"unknown"` (bu `jti` uchun yozuv umuman yo'q) yoki
    `"revoked"` (yozuv bor, lekin uzilgan yoki muddati o'tgan) bo'ladi.
    `"unknown"` va `"revoked"` ni ajratish kerak: birinchisi eski, `Device`
    jadvalidan oldin ochilgan sessiya, ikkinchisi ataylab yopilgani.
    """
    device = Device.objects.filter(refresh_jti=jti).first()
    if device is None:
        return None, "unknown"
    if not device.is_active or device.is_expired:
        if device.is_active:
            Device.objects.filter(pk=device.pk).update(is_active=False)
        return None, "revoked"
    return device, "ok"


def grandfather_device(refresh) -> Device | None:
    """`Device` jadvalidan oldin ochilgan sessiya uchun yozuv yaratadi.

    Baza eski mobil backupdan tiklanganda jonli refresh tokenlarning hech
    birida `Device` yozuvi yo'q. Ularni 401 bilan quvib yuborish butun
    foydalanuvchi bazasini bir kun ichida tizimdan chiqarardi.

    Limit qo'llanmaydi — bu allaqachon mavjud sessiya, yangi kirish emas.
    """
    from django.contrib.auth import get_user_model

    user_id = refresh.payload.get(settings.SIMPLE_JWT["USER_ID_CLAIM"])
    user = get_user_model().objects.filter(pk=user_id, is_active=True).first()
    if user is None:
        return None
    default = Device.Platform.MOBILE
    return Device.objects.create(
        user=user,
        platform=default,
        refresh_jti=refresh["jti"],
        label="(eski sessiya)",
        expires_at=_expiry(default),
    )


def rotate(device: Device, refresh) -> None:
    """Rotatsiyadan keyin yangi `jti` ni shu qurilmaga bog'laydi."""
    device.refresh_jti = refresh["jti"]
    device.save(update_fields=["refresh_jti", "last_seen"])
