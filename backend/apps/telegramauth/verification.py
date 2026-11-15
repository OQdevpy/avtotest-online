"""Telegram orqali kirish sessiyasi (Redis, TTL bilan).

Oqim: ilova (yoki admin panel) `start_session` dan token oladi va
`t.me/<bot>?start=<token>` havolasini ochadi. Raqam so'ralmaydi. Bot
`/start <token>` da sessiyani shu Telegram chatiga bog'laydi (`bind_chat`),
kontakt kelganda raqam va ismni sessiyaga yozib `verified` qiladi (O'zbekiston
raqami bo'lmasa — `mismatch`). Ilova holatni `status_of` orqali so'rab turadi
va `auth/telegram/claim/` tasdiqlangan sessiyani `consume_auth` bilan bir marta
tokenlarga almashtiradi.

Redis kalitlari:

* ``tgv:{token}``            -> JSON {phone, purpose, lang, status, telegram_id, full_name}
* ``tgv:chat:{telegram_id}`` -> token (bot kontaktni qaysi sessiyaga bog'lashini biladi)
* ``tgv:count:ip:{ip}``      -> shu IP dan ochilgan sessiyalar soni (cheklov uchun)
"""

from __future__ import annotations

import json
import secrets

from django.core.exceptions import ValidationError

from apps.accounts.models import normalize_phone

from . import otpstore
from .telegram import BOT_USERNAME

SESSION_TTL = 600
AUTH = "auth"
# Bir IP dan `COUNT_WINDOW` soniya ichida ko'pi bilan shuncha sessiya.
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


def _count_key(ip: str) -> str:
    return f"tgv:count:ip:{ip or '-'}"


def start_session(phone: str | None, purpose: str, lang: str, ip: str = "") -> str:
    """Yangi `pending` sessiya ochadi va tokenni qaytaradi.

    `auth` sessiyasida `phone=None` — raqam bot olgan kontaktdan yoziladi.
    """
    r = otpstore.client()
    count_key = _count_key(ip)
    count = r.incr(count_key)
    if count == 1:
        r.expire(count_key, COUNT_WINDOW)
    if count > MAX_SESSIONS:
        raise TooManySessions

    # token_urlsafe — faqat [A-Za-z0-9_-]; 24 bayt → 32 belgi (Telegram cheklovi 64).
    token = secrets.token_urlsafe(24)
    payload = {"phone": phone, "purpose": purpose, "lang": lang,
               "status": Status.PENDING, "telegram_id": None, "full_name": ""}
    r.set(_key(token), json.dumps(payload), ex=SESSION_TTL)
    return token


def get_session(token: str) -> dict | None:
    raw = otpstore.client().get(_key(token))
    return json.loads(raw) if raw else None


def status_of(token: str) -> str:
    session = get_session(token)
    return session["status"] if session else Status.EXPIRED


def mark(token: str, status: str, telegram_id: int | None = None, **fields) -> None:
    """Sessiya holatini (va qo'shimcha maydonlarni) yozadi. Tasdiqlangach yana
    `SESSION_TTL` yashaydi — foydalanuvchi ilovaga kech qaytsa ham kira oladi."""
    r = otpstore.client()
    session = get_session(token)
    if session is None:
        return
    session["status"] = status
    session.update(fields)
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


def consume_auth(token: str) -> dict | None:
    """Tasdiqlangan `auth` sessiyasini bir marta ishlatadi: o'chirib, qaytaradi."""
    if not token:
        return None
    session = get_session(token)
    if (session is None or session["status"] != Status.VERIFIED
            or session.get("purpose") != AUTH or not session.get("phone")):
        return None
    # `delete` 1 qaytarsa — aynan shu chaqiruv ishlatdi (parallel ikkinchisi 0 oladi).
    if otpstore.client().delete(_key(token)) != 1:
        return None
    return session


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


def resolve_contact(token: str, shared_raw: str, telegram_id: int,
                    full_name: str = "") -> tuple[str, str | None, str | None]:
    """Bot'ga kelgan kontaktni sessiyaga yozadi.

    Qaytaradi: ``(outcome, session_phone, shared_phone)``; outcome —
    ``verified`` | ``mismatch`` | ``foreign`` (O'zbekiston raqami emas) |
    ``expired`` (sessiya yo'q). ``foreign`` sessiyani ``mismatch`` qiladi.
    `auth` sessiyasida raqam solishtirilmaydi — kontakt raqami va ism yoziladi.
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
    if session.get("purpose") == AUTH:
        mark(token, Status.VERIFIED, telegram_id, phone=shared, full_name=full_name.strip())
        return "verified", shared, shared
    if shared != expected:
        mark(token, Status.MISMATCH, telegram_id)
        return "mismatch", expected, shared
    mark(token, Status.VERIFIED, telegram_id)
    return "verified", expected, shared
