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
def register_device(user, platform: str, label: str, refresh) -> Device:
    """Yangi sessiya yozadi. Limit to'lgan bo'lsa `DeviceLimitReached`."""
    platform = platform or Device.Platform.MOBILE
    if active_devices(user, platform).count() >= _limit(user, platform):
        raise DeviceLimitReached
    return Device.objects.create(
        user=user,
        platform=platform,
        refresh_jti=refresh["jti"],
        label=label or "",
        expires_at=_expiry(platform),
    )


def device_for_refresh(jti: str) -> Device | None:
    """Refresh uchun yaroqli qurilma; yo'q, o'chirilgan yoki muddati o'tgan bo'lsa None."""
    device = Device.objects.filter(refresh_jti=jti, is_active=True).first()
    if device is None:
        return None
    if device.is_expired:
        Device.objects.filter(pk=device.pk).update(is_active=False)
        return None
    return device


def rotate(device: Device, refresh) -> None:
    """Rotatsiyadan keyin yangi `jti` ni shu qurilmaga bog'laydi."""
    device.refresh_jti = refresh["jti"]
    device.save(update_fields=["refresh_jti", "last_seen"])
