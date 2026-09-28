"""Ijtimoiy kirish tokenini tekshirish.

HTTP so'rovlari monkeypatch bilan almashtiriladi (yangi test-kutubxona
qo'shmaslik uchun). Apple uchun haqiqiy RSA kalit generatsiya qilinadi, shuning
uchun imzo tekshiruvi rostakam sinovdan o'tadi.
"""

import base64
import hashlib
import hmac
import json
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from apps.accounts import social
from apps.accounts.social import SocialVerificationError, verify_social_token

pytestmark = pytest.mark.django_db

APPLE_AUD = "uz.avtotest.yolchi"
GOOGLE_CLIENT = "123.apps.googleusercontent.com"
BOT_TOKEN = "123456:TEST-BOT-TOKEN"


@pytest.fixture
def apple_keys(settings, monkeypatch):
    """Apple JWK uchun haqiqiy RSA kalit juftligi."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    settings.APPLE_BUNDLE_ID = APPLE_AUD

    def fake_apple_keys():
        return {"kid-1": key.public_key()}

    monkeypatch.setattr(social, "_apple_public_keys", fake_apple_keys)
    return key


def apple_token(key, *, aud=APPLE_AUD, iss="https://appleid.apple.com",
                sub="apple-uid-1", email="a@b.c", exp_offset=3600):
    return jwt.encode(
        {"iss": iss, "aud": aud, "sub": sub, "email": email,
         "exp": int(time.time()) + exp_offset, "iat": int(time.time())},
        key, algorithm="RS256", headers={"kid": "kid-1"},
    )


def telegram_payload(bot_token=BOT_TOKEN, *, auth_date=None, tamper=False):
    data = {"id": "555", "first_name": "Ali",
            "auth_date": str(auth_date or int(time.time()))}
    check = "\n".join(f"{k}={data[k]}" for k in sorted(data))
    secret = hashlib.sha256(bot_token.encode()).digest()
    data["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    if tamper:
        data["first_name"] = "Vali"
    return data


# --- Apple ------------------------------------------------------------------

def test_valid_apple_token_returns_uid_and_email(apple_keys):
    result = verify_social_token("apple", apple_token(apple_keys), "apple-uid-1")
    assert result == {"uid": "apple-uid-1", "email": "a@b.c"}


def test_apple_token_with_wrong_audience_rejected(apple_keys):
    with pytest.raises(SocialVerificationError):
        verify_social_token("apple", apple_token(apple_keys, aud="boshqa"), "apple-uid-1")


def test_apple_token_with_wrong_issuer_rejected(apple_keys):
    with pytest.raises(SocialVerificationError):
        verify_social_token("apple", apple_token(apple_keys, iss="https://evil"), "apple-uid-1")


def test_apple_token_with_bad_signature_rejected(apple_keys):
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(SocialVerificationError):
        verify_social_token("apple", apple_token(other), "apple-uid-1")


def test_expired_apple_token_rejected(apple_keys):
    with pytest.raises(SocialVerificationError):
        verify_social_token("apple", apple_token(apple_keys, exp_offset=-10), "apple-uid-1")


def test_apple_token_with_mismatched_uid_rejected(apple_keys):
    with pytest.raises(SocialVerificationError):
        verify_social_token("apple", apple_token(apple_keys, sub="boshqa"), "apple-uid-1")


# --- Google -----------------------------------------------------------------

class FakeResponse:
    def __init__(self, payload, status_code):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


def fake_tokeninfo(monkeypatch, payload, status_code=200):
    monkeypatch.setattr(
        social, "_http_get", lambda url, **kw: FakeResponse(payload, status_code)
    )


def test_valid_google_token_returns_uid_and_email(settings, monkeypatch):
    settings.GOOGLE_CLIENT_IDS = [GOOGLE_CLIENT]
    fake_tokeninfo(monkeypatch, {"aud": GOOGLE_CLIENT, "sub": "g-1", "email": "g@b.c"})
    assert verify_social_token("google", "tok", "g-1") == {"uid": "g-1", "email": "g@b.c"}


def test_google_tokeninfo_mismatched_sub_rejected(settings, monkeypatch):
    settings.GOOGLE_CLIENT_IDS = [GOOGLE_CLIENT]
    fake_tokeninfo(monkeypatch, {"aud": GOOGLE_CLIENT, "sub": "boshqa"})
    with pytest.raises(SocialVerificationError):
        verify_social_token("google", "tok", "g-1")


def test_google_wrong_audience_rejected(settings, monkeypatch):
    settings.GOOGLE_CLIENT_IDS = [GOOGLE_CLIENT]
    fake_tokeninfo(monkeypatch, {"aud": "boshqa-client", "sub": "g-1"})
    with pytest.raises(SocialVerificationError):
        verify_social_token("google", "tok", "g-1")


def test_google_http_error_rejected(settings, monkeypatch):
    settings.GOOGLE_CLIENT_IDS = [GOOGLE_CLIENT]
    fake_tokeninfo(monkeypatch, {"error": "invalid_token"}, status_code=400)
    with pytest.raises(SocialVerificationError):
        verify_social_token("google", "tok", "g-1")


# --- Telegram ---------------------------------------------------------------

def test_valid_telegram_payload_accepted(settings):
    settings.TELEGRAM_BOT_TOKEN = BOT_TOKEN
    payload = telegram_payload()
    token = base64.b64encode(json.dumps(payload).encode()).decode()
    assert verify_social_token("telegram", token, "555")["uid"] == "555"


def test_telegram_hash_mismatch_rejected(settings):
    settings.TELEGRAM_BOT_TOKEN = BOT_TOKEN
    token = base64.b64encode(json.dumps(telegram_payload(tamper=True)).encode()).decode()
    with pytest.raises(SocialVerificationError):
        verify_social_token("telegram", token, "555")


def test_stale_telegram_auth_date_rejected(settings):
    settings.TELEGRAM_BOT_TOKEN = BOT_TOKEN
    old = int(time.time()) - 60 * 60 * 48
    token = base64.b64encode(json.dumps(telegram_payload(auth_date=old)).encode()).decode()
    with pytest.raises(SocialVerificationError):
        verify_social_token("telegram", token, "555")


# --- Sozlanmagan va noma'lum provayder --------------------------------------

def test_unknown_provider_rejected():
    with pytest.raises(SocialVerificationError):
        verify_social_token("vkontakte", "tok", "1")


def test_unconfigured_provider_rejected(settings):
    settings.GOOGLE_CLIENT_IDS = []
    with pytest.raises(SocialVerificationError):
        verify_social_token("google", "tok", "g-1")


# --- View -------------------------------------------------------------------

def test_social_login_rejects_unverified_token(api):
    response = api.post("/api/v1/auth/social/",
                        {"provider": "google", "uid": "123", "token": "bad"},
                        format="json")
    assert response.status_code == 401


def test_social_login_requires_token(api):
    response = api.post("/api/v1/auth/social/",
                        {"provider": "google", "uid": "123"}, format="json")
    assert response.status_code in (400, 401)


def test_social_login_succeeds_with_verified_token(api, settings, monkeypatch):
    settings.GOOGLE_CLIENT_IDS = [GOOGLE_CLIENT]
    fake_tokeninfo(monkeypatch, {"aud": GOOGLE_CLIENT, "sub": "g-1", "email": "g@b.c"})
    response = api.post("/api/v1/auth/social/",
                        {"provider": "google", "uid": "g-1", "token": "tok",
                         "platform": "mobile"},
                        format="json")
    assert response.status_code == 201
    assert "access" in response.json()["tokens"]
