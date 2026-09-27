"""Redis'da saqlanadigan bir martalik tasdiqlash kodlari (OTP).

Kodlar bazaga emas, Redis'ga TTL bilan yoziladi — tez va o'z-o'zidan
muddati o'tadi. Bazada faqat ``TelegramAccount`` bog'lanishi (telegram_id
<-> phone <-> user, til) saqlanadi.

Redis kalitlari:

* ``otp:{purpose}:{phone}``   -> JSON {code_hash, attempts, telegram_id}
      Kodning o'zi (hash), urinishlar soni. TTL = CODE_TTL_SECONDS.
* ``otp:cooldown:{purpose}:{phone}`` -> "1"
      Qayta yuborishgacha kutish. TTL = RESEND_COOLDOWN_SECONDS.
* ``otp:token:{token}``       -> JSON {phone, purpose}
      Verify muvaffaqiyatli bo'lgach beriladigan bir martalik token
      (reset qadami uchun). TTL = TOKEN_TTL_SECONDS.

Kod hech qachon ochiq holda saqlanmaydi — faqat HMAC-SHA256 hash.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets

import redis
from django.conf import settings

# --- Muddatlar / cheklovlar (frontenddagi qiymatlar bilan mos) -------------
CODE_TTL_SECONDS = 120
TOKEN_TTL_SECONDS = 600
RESEND_COOLDOWN_SECONDS = 60
MAX_ATTEMPTS = 5


# --- Redis ulanishi (jarayon davomida bitta pool) --------------------------
_client: redis.Redis | None = None


def client() -> redis.Redis:
    global _client
    if _client is None:
        url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
        _client = redis.from_url(url, decode_responses=True)
    return _client


# --- Yordamchilar ----------------------------------------------------------

def _code_hash(phone: str, code: str) -> str:
    """Kodni ochiq matnda saqlamaslik uchun HMAC-SHA256 (SECRET_KEY kalit)."""
    msg = f"{phone}:{code}".encode()
    key = settings.SECRET_KEY.encode()
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def _code_key(purpose: str, phone: str) -> str:
    return f"otp:{purpose}:{phone}"


def _cooldown_key(purpose: str, phone: str) -> str:
    return f"otp:cooldown:{purpose}:{phone}"


def _token_key(token: str) -> str:
    return f"otp:token:{token}"


# --- Ommaviy API -----------------------------------------------------------

def cooldown_left(purpose: str, phone: str) -> int:
    """Qayta yuborishgacha qolgan soniya (0 bo'lsa — yuborish mumkin)."""
    ttl = client().ttl(_cooldown_key(purpose, phone))
    return ttl if ttl and ttl > 0 else 0


def issue_code(purpose: str, phone: str, telegram_id: int) -> str:
    """Yangi 6 xonali kod yaratadi, Redis'ga TTL bilan yozadi va ochiq
    kodni qaytaradi (Telegram'ga yuborish uchun; hech qayerda saqlanmaydi).

    Eski kodni (agar bo'lsa) almashtiradi. Qayta yuborish "cooldown"
    kalitini o'rnatadi.
    """
    plain = f"{secrets.randbelow(1_000_000):06d}"
    payload = json.dumps(
        {
            "code_hash": _code_hash(phone, plain),
            "attempts": 0,
            "telegram_id": telegram_id,
        }
    )
    r = client()
    r.set(_code_key(purpose, phone), payload, ex=CODE_TTL_SECONDS)
    r.set(_cooldown_key(purpose, phone), "1", ex=RESEND_COOLDOWN_SECONDS)
    return plain


class VerifyResult:
    OK = "ok"
    EXPIRED = "expired"
    TOO_MANY = "too_many"
    INVALID = "invalid"


def verify_code(purpose: str, phone: str, code: str) -> tuple[str, str | None]:
    """Kodni tekshiradi.

    Qaytaradi: ``(status, token)`` — status VerifyResult dan biri.
    Muvaffaqiyatda (OK) bir martalik token ham qaytadi va kod o'chiriladi.
    """
    r = client()
    key = _code_key(purpose, phone)
    raw = r.get(key)
    if raw is None:
        return VerifyResult.EXPIRED, None

    data = json.loads(raw)
    if data.get("attempts", 0) >= MAX_ATTEMPTS:
        r.delete(key)
        return VerifyResult.TOO_MANY, None

    expected = data.get("code_hash", "")
    if not hmac.compare_digest(expected, _code_hash(phone, code)):
        # Urinishni oshiramiz, ammo TTL'ni saqlab qolamiz.
        data["attempts"] = data.get("attempts", 0) + 1
        ttl = r.ttl(key)
        if ttl and ttl > 0:
            r.set(key, json.dumps(data), ex=ttl)
        else:
            r.delete(key)
        return VerifyResult.INVALID, None

    # To'g'ri — kodni o'chiramiz, bir martalik token beramiz.
    r.delete(key)
    token = secrets.token_urlsafe(32)
    r.set(
        _token_key(token),
        json.dumps({"phone": phone, "purpose": purpose}),
        ex=TOKEN_TTL_SECONDS,
    )
    return VerifyResult.OK, token


def consume_token(token: str, phone: str, purpose: str) -> bool:
    """Reset qadamida tokenni tekshiradi va bir martalik ishlatadi.

    Token mos kelsa — o'chiradi va True qaytaradi (qayta ishlatib bo'lmaydi).
    """
    r = client()
    key = _token_key(token)
    raw = r.get(key)
    if raw is None:
        return False
    data = json.loads(raw)
    if data.get("phone") != phone or data.get("purpose") != purpose:
        return False
    r.delete(key)
    return True
