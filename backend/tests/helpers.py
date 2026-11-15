"""Testlar uchun umumiy yordamchilar."""

import itertools

from apps.telegramauth import verification

CLAIM = "/api/v1/auth/telegram/claim/"

# Har kirish boshqa IP dan — sessiya cheklovi (IP ga 5 ta) testlarga xalaqit bermasin.
_ips = itertools.count(1)


def telegram_token(phone: str, name: str = "", telegram_id: int = 7) -> str:
    """Bot kontaktni qabul qilgan (tasdiqlangan) kirish sessiyasi tokeni."""
    n = next(_ips)
    token = verification.start_session(None, "auth", "uz", ip=f"10.{n // 65536 % 256}."
                                       f"{n // 256 % 256}.{n % 256}")
    verification.resolve_contact(token, phone, telegram_id, name)
    return token


def telegram_login(api, phone: str, platform: str = "", label: str = "", **extra):
    """Telegram orqali kirish (`fake_redis` fixture kerak). DRF javobini qaytaradi."""
    body = {"token": telegram_token(phone), **extra}
    if platform:
        body["platform"] = platform
    if label:
        body["device_label"] = label
    return api.post(CLAIM, body, format="json")
