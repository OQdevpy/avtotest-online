"""Eski avtotest bazasidan (avtotest-tayyorlov.uz) hisobni olish.

Eski ilova (1.0.x) eski backendda ishlashda davom etadi. Yangi ilovada
Telegram orqali kirgan raqam bu bazada bo'lmasa, eski bazadan qidiriladi va
topilsa ism, til va PRO muddati yangi hisobga ko'chiriladi. Eski bazaga faqat
o'qish uchun ulaniladi — hech narsa yozilmaydi.

Ulanish: `.env` da `LEGACY_DATABASE_URL` (bo'sh bo'lsa — o'chirilgan).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone as dt_timezone

from django.conf import settings
from django.db import DatabaseError, connections
from django.utils import timezone
from django.utils.dateparse import parse_datetime

logger = logging.getLogger(__name__)

COLUMNS = ("full_name", "language", "is_pro", "pro_until", "is_active", "date_joined")
# Eski bazada qoraqalpoq (qq) ham bor edi — yangisida lotin o'zbekcha.
LANGUAGES = {"uz": "uz", "kr": "kr", "ru": "ru", "qq": "uz"}


def _alias() -> str:
    return getattr(settings, "LEGACY_DB_ALIAS", "legacy")


def _aware(value):
    if isinstance(value, str):
        value = parse_datetime(value)
    if isinstance(value, datetime) and timezone.is_naive(value):
        value = timezone.make_aware(value, dt_timezone.utc)
    return value


def legacy_user(phone: str) -> dict | None:
    """Eski bazadagi o'quvchi ma'lumoti yoki None (topilmasa/ulanib bo'lmasa)."""
    alias = _alias()
    if alias not in settings.DATABASES:
        return None
    try:
        with connections[alias].cursor() as cursor:
            cursor.execute(
                f"SELECT {', '.join(COLUMNS)} FROM accounts_user "
                "WHERE phone = %s AND role = %s",
                [phone, "student"],
            )
            row = cursor.fetchone()
    except DatabaseError:
        # Eski baza ishlamasa ham kirish to'xtamasin — oddiy yangi hisob ochiladi.
        logger.warning("Eski bazadan %s ni o'qib bo'lmadi", phone, exc_info=True)
        return None
    if row is None:
        return None
    data = dict(zip(COLUMNS, row))
    data["language"] = LANGUAGES.get((data["language"] or "").lower(), "uz")
    data["pro_until"] = _aware(data["pro_until"])
    data["date_joined"] = _aware(data["date_joined"])
    data["is_pro"] = bool(data["is_pro"])
    data["is_active"] = bool(data["is_active"])
    return data


def pro_active(data: dict) -> bool:
    if not data["is_pro"]:
        return False
    return data["pro_until"] is None or data["pro_until"] > timezone.now()
