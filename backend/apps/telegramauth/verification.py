"""Telegram orqali raqamni tasdiqlash sessiyasi (Redis, TTL bilan).

Oqim: ilova `start_session` dan token oladi va `t.me/<bot>?start=<token>`
havolasini ochadi. Bot `/start <token>` da sessiyani shu Telegram chatiga
bog'laydi (`bind_chat`), kontakt kelganda raqamni solishtirib sessiyani
`verified` yoki `mismatch` qiladi. Ilova holatni `status_of` orqali so'rab
turadi; `register/` va `reset-password/` tasdiqlangan tokenni `consume`
bilan bir marta ishlatadi.

Redis kalitlari:

* ``tgv:{token}``            -> JSON {phone, purpose, lang, status, telegram_id}
* ``tgv:chat:{telegram_id}`` -> token (bot kontaktni qaysi sessiyaga bog'lashini biladi)
* ``tgv:count:{phone}``      -> shu raqamga ochilgan sessiyalar soni (cheklov uchun)
"""

from __future__ import annotations

import json
import secrets

from django.core.exceptions import ValidationError

from apps.accounts.models import normalize_phone

from . import otpstore
from .telegram import BOT_USERNAME

SESSION_TTL = 600
# Bir raqamga `COUNT_WINDOW` soniya ichida ko'pi bilan shuncha sessiya.
MAX_SESSIONS = 5
COUNT_WINDOW = 600


class Status:
    PENDING = "pending"
    VERIFIED = "verified"
    MISMATCH = "mismatch"
    EXPIRED = "expired"


class TooManySessions(Exception):
    """Bir raqamga juda ko'p tasdiqlash sessiyasi ochildi."""


def _key(token: str) -> str:
    return f"tgv:{token}"


def _chat_key(telegram_id: int) -> str:
    return f"tgv:chat:{telegram_id}"


def _count_key(phone: str) -> str:
    return f"tgv:count:{phone}"


def start_session(phone: str, purpose: str, lang: str) -> str:
    """Yangi `pending` sessiya ochadi va tokenni qaytaradi."""
    r = otpstore.client()
    count_key = _count_key(phone)
    count = r.incr(count_key)
    if count == 1:
        r.expire(count_key, COUNT_WINDOW)
    if count > MAX_SESSIONS:
        raise TooManySessions

    # token_urlsafe — faqat [A-Za-z0-9_-]; 24 bayt → 32 belgi (Telegram cheklovi 64).
    token = secrets.token_urlsafe(24)
    payload = {"phone": phone, "purpose": purpose, "lang": lang,
               "status": Status.PENDING, "telegram_id": None}
    r.set(_key(token), json.dumps(payload), ex=SESSION_TTL)
    return token


def get_session(token: str) -> dict | None:
    raw = otpstore.client().get(_key(token))
    return json.loads(raw) if raw else None


def status_of(token: str) -> str:
    session = get_session(token)
    return session["status"] if session else Status.EXPIRED


def mark(token: str, status: str, telegram_id: int | None = None) -> None:
    """Sessiya holatini yozadi. Tasdiqlangach yana `SESSION_TTL` yashaydi —
    foydalanuvchi ilovaga kech qaytsa ham ro'yxatdan o'ta oladi."""
    r = otpstore.client()
    session = get_session(token)
    if session is None:
        return
    session["status"] = status
    if telegram_id is not None:
        session["telegram_id"] = telegram_id
    if status == Status.VERIFIED:
        ttl = SESSION_TTL
    else:
        ttl = r.ttl(_key(token))
        ttl = ttl if ttl and ttl > 0 else SESSION_TTL
    r.set(_key(token), json.dumps(session), ex=ttl)


def consume(token: str, phone: str, purpose: str) -> bool:
    """Tasdiqlangan va mos sessiyani bir marta ishlatadi (o'chiradi)."""
    if not token:
        return False
    session = get_session(token)
    if (session is None or session["status"] != Status.VERIFIED
            or session["phone"] != phone or session["purpose"] != purpose):
        return False
    # `delete` 1 qaytarsa — aynan shu chaqiruv ishlatdi (parallel ikkinchisi 0 oladi).
    return otpstore.client().delete(_key(token)) == 1


def bind_chat(telegram_id: int, token: str) -> None:
    otpstore.client().set(_chat_key(telegram_id), token, ex=SESSION_TTL)


def chat_token(telegram_id: int) -> str | None:
    return otpstore.client().get(_chat_key(telegram_id))


def unbind_chat(telegram_id: int) -> None:
    """Kontakt qabul qilingach — keyingi kontakt eski oqimga tushsin."""
    otpstore.client().delete(_chat_key(telegram_id))


def bot_link(token: str) -> str:
    return f"https://t.me/{BOT_USERNAME}?start={token}"


def mask_phone(phone: str) -> str:
    """`+998901234567` -> `+998 90 ***-45-67` (bot xabarlarida)."""
    return f"{phone[:4]} {phone[4:6]} ***-{phone[9:11]}-{phone[11:13]}"


def resolve_contact(token: str, shared_raw: str,
                    telegram_id: int) -> tuple[str, str | None, str | None]:
    """Bot'ga kelgan kontaktni sessiyadagi raqam bilan solishtiradi.

    Qaytaradi: ``(outcome, session_phone, shared_phone)``; outcome —
    ``verified`` | ``mismatch`` | ``foreign`` (O'zbekiston raqami emas) |
    ``expired`` (sessiya yo'q). ``foreign`` ham sessiyani ``mismatch`` qiladi.
    Kontakt aynan yuboruvchiniki ekani bot'da oldinroq tekshiriladi.
    """
    session = get_session(token)
    if session is None:
        return "expired", None, None
    expected = session["phone"]
    try:
        shared = normalize_phone(shared_raw)
    except ValidationError:
        mark(token, Status.MISMATCH, telegram_id)
        return "foreign", expected, None
    if shared != expected:
        mark(token, Status.MISMATCH, telegram_id)
        return "mismatch", expected, shared
    mark(token, Status.VERIFIED, telegram_id)
    return "verified", expected, shared
