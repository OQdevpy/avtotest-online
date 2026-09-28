"""Ijtimoiy kirish tokenlarini server tomonda tekshirish.

Mijoz yuborgan `uid` ga hech qachon ishonilmaydi: har bir provayder uchun token
o'z manbasida tasdiqlanadi. Provayder sozlanmagan bo'lsa kirish ham ochilmaydi —
tekshiruvsiz ishlash imkoni yo'q.

- **Apple:** identity token — RS256 imzosi Apple JWK'lari bilan, `aud` bundle id,
  `iss` `https://appleid.apple.com`.
- **Google:** `tokeninfo` endpointi — `aud` ruxsat etilgan client id'lar ichida.
- **Telegram:** login-widget `hash` i — HMAC-SHA256, kalit `sha256(bot_token)`.
"""

import base64
import binascii
import hashlib
import hmac
import json
import time

import httpx
import jwt
from django.conf import settings
from jwt import PyJWKClient

APPLE_ISSUER = "https://appleid.apple.com"
APPLE_KEYS_URL = "https://appleid.apple.com/auth/keys"
GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
TELEGRAM_MAX_AGE_SECONDS = 24 * 60 * 60
HTTP_TIMEOUT_SECONDS = 10


class SocialVerificationError(Exception):
    """Token provayder tomonidan tasdiqlanmadi."""


def _http_get(url: str, **kwargs):
    return httpx.get(url, timeout=HTTP_TIMEOUT_SECONDS, **kwargs)


_apple_jwk_client: PyJWKClient | None = None


def _apple_public_keys() -> dict:
    """Apple JWK'lari, `kid` bo'yicha. PyJWKClient ularni o'zi keshlaydi."""
    global _apple_jwk_client
    if _apple_jwk_client is None:
        _apple_jwk_client = PyJWKClient(APPLE_KEYS_URL, cache_keys=True, lifespan=86400)
    return {
        key.key_id: key.key
        for key in _apple_jwk_client.get_signing_keys()
    }


def _verify_apple(token: str, uid: str) -> dict:
    audience = getattr(settings, "APPLE_BUNDLE_ID", "")
    if not audience:
        raise SocialVerificationError("Apple kirish sozlanmagan (APPLE_BUNDLE_ID).")

    try:
        kid = jwt.get_unverified_header(token).get("kid")
    except jwt.PyJWTError as exc:
        raise SocialVerificationError("Apple tokeni o'qilmadi.") from exc

    key = _apple_public_keys().get(kid)
    if key is None:
        raise SocialVerificationError("Apple kaliti topilmadi.")

    try:
        claims = jwt.decode(
            token, key, algorithms=["RS256"], audience=audience, issuer=APPLE_ISSUER
        )
    except jwt.PyJWTError as exc:
        raise SocialVerificationError("Apple tokeni yaroqsiz.") from exc

    if claims.get("sub") != uid:
        raise SocialVerificationError("Apple tokeni boshqa hisobga tegishli.")
    return {"uid": claims["sub"], "email": claims.get("email", "")}


def _verify_google(token: str, uid: str) -> dict:
    client_ids = list(getattr(settings, "GOOGLE_CLIENT_IDS", []) or [])
    if not client_ids:
        raise SocialVerificationError("Google kirish sozlanmagan (GOOGLE_CLIENT_IDS).")

    try:
        response = _http_get(GOOGLE_TOKENINFO_URL, params={"id_token": token})
    except httpx.HTTPError as exc:
        raise SocialVerificationError("Google bilan bog'lanib bo'lmadi.") from exc

    if response.status_code != 200:
        raise SocialVerificationError("Google tokeni yaroqsiz.")

    claims = response.json()
    if claims.get("aud") not in client_ids:
        raise SocialVerificationError("Google tokeni boshqa ilovaga tegishli.")
    if claims.get("sub") != uid:
        raise SocialVerificationError("Google tokeni boshqa hisobga tegishli.")
    return {"uid": claims["sub"], "email": claims.get("email", "")}


def _verify_telegram(token: str, uid: str) -> dict:
    bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        raise SocialVerificationError("Telegram kirish sozlanmagan (TELEGRAM_BOT_TOKEN).")

    try:
        payload = json.loads(base64.b64decode(token))
    except (ValueError, binascii.Error) as exc:
        raise SocialVerificationError("Telegram ma'lumoti o'qilmadi.") from exc
    if not isinstance(payload, dict):
        raise SocialVerificationError("Telegram ma'lumoti o'qilmadi.")

    received = payload.pop("hash", "")
    check_string = "\n".join(f"{k}={payload[k]}" for k in sorted(payload))
    secret = hashlib.sha256(bot_token.encode()).digest()
    expected = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received):
        raise SocialVerificationError("Telegram imzosi mos kelmadi.")

    try:
        auth_date = int(payload.get("auth_date", 0))
    except (TypeError, ValueError) as exc:
        raise SocialVerificationError("Telegram auth_date yaroqsiz.") from exc
    if time.time() - auth_date > TELEGRAM_MAX_AGE_SECONDS:
        raise SocialVerificationError("Telegram tasdiqlash muddati o'tgan.")

    if str(payload.get("id")) != str(uid):
        raise SocialVerificationError("Telegram ma'lumoti boshqa hisobga tegishli.")
    return {"uid": str(payload["id"]), "email": payload.get("email", "")}


_VERIFIERS = {
    "apple": _verify_apple,
    "google": _verify_google,
    "telegram": _verify_telegram,
}


def verify_social_token(provider: str, token: str, uid: str) -> dict:
    """Tasdiqlangan `{"uid", "email"}`; aks holda `SocialVerificationError`."""
    verifier = _VERIFIERS.get(provider)
    if verifier is None:
        raise SocialVerificationError(f"'{provider}' provayderi qo'llab-quvvatlanmaydi.")
    if not token:
        raise SocialVerificationError("Provayder tokeni yuborilmadi.")
    return verifier(token, uid)
