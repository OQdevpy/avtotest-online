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


class Section(models.TextChoices):
    """Ilovadagi bo'limlar — PRO'siz foydalanuvchiga yopiladiganlari admin'da tanlanadi."""
    TOPICS = "topics", "Mavzular va darslar"
    EXAM = "exam", "Imtihon simulyatori"
    HARD = "hard", "Qiyin savollar"
    TICKETS = "tickets", "Biletlar"
    MISTAKES = "mistakes", "Xatolar"
    SAVED = "saved", "Saqlanganlar"
    OCTAGON = "octagon", "Oktagon"
    STATS = "stats", "Statistika"


DEFAULT_LOCKED = [Section.TOPICS, Section.EXAM, Section.HARD]


def default_locked():
    return [str(s) for s in DEFAULT_LOCKED]


class AppSettings(models.Model):
    """Ilovaning sotuv sozlamalari (bitta yozuv). Ilova `app/config/` dan o'qiydi.

    Standart qiymatlar hozirgi xatti-harakat bilan bir xil — admin o'zgartirmaguncha
    hech narsa o'zgarmaydi.
    """

    guest_days = models.PositiveSmallIntegerField(
        "Mehmon sinovi (kun)", default=3,
        help_text="Ro'yxatdan o'tmagan foydalanuvchi necha kun hamma narsadan foydalanadi. "
                  "Yangi mehmonlarga qo'llanadi.",
    )
    welcome_pro_days = models.PositiveSmallIntegerField(
        "Ro'yxatdan o'tganda bepul PRO (kun)", default=12,
        help_text="Telegram orqali yangi hisob ochganda beriladigan bepul PRO. "
                  "0 — sovg'a yo'q: bo'limlar darhol yopiladi va to'lov taklif qilinadi.",
    )
    paywall_after_signup = models.BooleanField(
        "Ro'yxatdan o'tgach to'lov oynasini ko'rsatish", default=False,
        help_text="Yoqilsa, yangi hisob ochilgan zahoti ilova tariflar oynasini ochadi "
                  "(PRO'si bo'lmasa).",
    )
    locked_sections = models.JSONField(
        "PRO'siz yopiq bo'limlar", default=default_locked, blank=True,
        help_text="Belgilangan bo'limlar PRO'siz foydalanuvchiga qulf bilan ko'rinadi.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ilova sozlamalari"
        verbose_name_plural = "Ilova sozlamalari"

    def __str__(self) -> str:
        return "Ilova sozlamalari"

    def save(self, *args, **kwargs):
        self.pk = 1  # yagona yozuv
        allowed = set(Section.values)
        self.locked_sections = [s for s in (self.locked_sections or []) if s in allowed]
        super().save(*args, **kwargs)

    @classmethod
    def current(cls) -> "AppSettings":
        obj = cls.objects.filter(pk=1).first()
        return obj if obj is not None else cls(pk=1)
