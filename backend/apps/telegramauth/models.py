"""Telegram orqali telefon tasdiqlash uchun modellar.

Bazada faqat bitta model bor:

* ``TelegramAccount`` — bot'da "kontaktni ulashish" tugmasi bosilganda
  yaratiladigan bog'lanish: ``telegram_id`` <-> ``phone``. Kod aynan shu
  bog'langan Telegram chatiga yuboriladi.

Bir martalik kodlar (OTP) esa bazaga emas, **Redis**'ga TTL bilan yoziladi —
``apps.telegramauth.otpstore`` moduliga qarang.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models


class Purpose(models.TextChoices):
    REGISTER = "register", "Ro'yxatdan o'tish"
    RESET = "reset", "Parolni tiklash"


class BotLanguage(models.TextChoices):
    """Bot ichidagi tillar. Ilova tillari (uz/kr/qq/ru) shu yerga xaritalanadi."""

    UZ = "uz", "O'zbekcha (lotin)"
    KR = "kr", "Ўзбекча (кирилл)"
    RU = "ru", "Русский"


class TelegramAccount(models.Model):
    """Telegram foydalanuvchisi <-> telefon raqami bog'lanishi."""

    telegram_id = models.BigIntegerField(unique=True, db_index=True)
    phone = models.CharField(max_length=13, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="telegram_accounts",
    )
    language = models.CharField(
        max_length=2, choices=BotLanguage.choices, default=BotLanguage.UZ
    )
    username = models.CharField(max_length=64, blank=True)
    full_name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Telegram hisob"
        verbose_name_plural = "Telegram hisoblar"

    def __str__(self) -> str:
        return f"{self.telegram_id} <-> {self.phone or '(raqam yo‘q)'}"
