"""Mobil ilova versiyalari: majburiy yangilash va kim qaysi versiyada.

Shef admin'da har platforma uchun `min_version` (bundan past — ilova ishlamaydi)
va `latest_version` (bundan past — yangilash taklif qilinadi) ni o'zgartiradi.
Ilova ishga tushganda `app/version/` ni so'raydi va o'z versiyasini yuboradi —
kirgan foydalanuvchining versiyasi `UserAppVersion` ga yoziladi.
"""

from django.conf import settings
from django.db import models

STORE_URLS = {
    "android": "https://play.google.com/store/apps/details?id=com.oqdevpy.avtotest_tayyorlov",
    "ios": "https://apps.apple.com/app/id6809177447",
}


def parse_version(value: str) -> tuple[int, ...] | None:
    """'1.2.0' → (1, 2, 0). Yaroqsiz bo'lsa None."""
    parts = (value or "").strip().split(".")
    if not parts or not all(p.isdigit() for p in parts):
        return None
    numbers = [int(p) for p in parts]
    return tuple(numbers + [0] * (3 - len(numbers)))  # 1.2 == 1.2.0


class Platform(models.TextChoices):
    ANDROID = "android", "Android"
    IOS = "ios", "iOS"


class AppRelease(models.Model):
    platform = models.CharField("Platforma", max_length=10, choices=Platform.choices, unique=True)
    min_version = models.CharField(
        "Minimal versiya", max_length=20, blank=True,
        help_text="Bundan past versiya ishlamaydi — foydalanuvchi yangilashga majbur. "
                  "Bo'sh — cheklov yo'q. Masalan: 1.2.0",
    )
    latest_version = models.CharField(
        "Oxirgi versiya", max_length=20, blank=True,
        help_text="Bundan past versiyaga yangilash taklif qilinadi (majburiy emas).",
    )
    store_url = models.URLField(
        "Do'kon havolasi", blank=True,
        help_text="Bo'sh — standart Google Play / App Store sahifasi.",
    )
    review_mode = models.BooleanField(
        "Do'kon tekshiruvi rejimi", default=False,
        help_text="Yoqilsa kirish ekranida «Test hisob bilan kirish» chiqadi (Apple/Google "
                  "tekshiruvchisi uchun). Ilova tasdiqlangach o'chiring — faqat Telegram qoladi.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ilova relizi"
        verbose_name_plural = "Ilova relizlari"

    def __str__(self) -> str:
        return f"{self.get_platform_display()}: min {self.min_version or '—'}, oxirgi {self.latest_version or '—'}"

    def clean(self):
        from django.core.exceptions import ValidationError

        errors = {}
        for field in ("min_version", "latest_version"):
            value = getattr(self, field)
            if value and parse_version(value) is None:
                errors[field] = "Versiya 1.2.0 ko'rinishida bo'lishi kerak."
        if errors:
            raise ValidationError(errors)

    @classmethod
    def review_mode_on(cls, platform: str) -> bool:
        return cls.objects.filter(platform=(platform or "").lower(), review_mode=True).exists()

    @property
    def resolved_store_url(self) -> str:
        return self.store_url or STORE_URLS.get(self.platform, "")


class UserAppVersion(models.Model):
    """Foydalanuvchi oxirgi marta qaysi ilova versiyasidan kirgan."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="app_version",
        verbose_name="Foydalanuvchi",
    )
    platform = models.CharField("Platforma", max_length=10, choices=Platform.choices)
    version = models.CharField("Versiya", max_length=20, db_index=True)
    last_seen = models.DateTimeField("Oxirgi marta", auto_now=True, db_index=True)

    class Meta:
        verbose_name = "Foydalanuvchi ilova versiyasi"
        verbose_name_plural = "Foydalanuvchilar ilova versiyalari"
        ordering = ("-last_seen",)

    def __str__(self) -> str:
        return f"{self.user} — {self.platform} {self.version}"
