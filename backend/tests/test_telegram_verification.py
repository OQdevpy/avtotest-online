"""Telegram orqali kirish sessiyasi — start/status va bot kontakt mantig'i.

Sessiya raqamsiz ochiladi; raqam va ism bot olgan kontaktdan yoziladi.
"""

import re

from django.conf import settings

from apps.telegramauth import verification

START = "/api/v1/auth/telegram/start/"


def status_url(token):
    return f"/api/v1/auth/telegram/status/{token}/"


def start(api, ip="10.0.0.1"):
    return api.post(START, {"lang": "uz"}, format="json", HTTP_X_REAL_IP=ip)


def new_token():
    return verification.start_session(None, "auth", "uz", ip="10.0.0.1")


def test_start_without_phone(api, db, fake_redis):
    r = start(api)
    assert r.status_code == 200, r.data
    token = r.data["token"]
    assert r.data["link"] == f"https://t.me/{settings.TELEGRAM_BOT_USERNAME}?start={token}"
    assert re.fullmatch(r"[A-Za-z0-9_-]{1,64}", token)
    assert r.data["expires_in"] == 600
    session = verification.get_session(token)
    assert session["purpose"] == "auth"
    assert session["phone"] is None


def test_start_rate_limited_by_ip(api, db, fake_redis):
    for _ in range(5):
        assert start(api).status_code == 200
    r = start(api)
    assert r.status_code == 429
    assert r.data["code"] == "too_many"
    # Boshqa IP cheklovga tushmaydi.
    assert start(api, ip="10.0.0.2").status_code == 200


def test_status_flow(api, db, fake_redis):
    token = start(api).data["token"]
    assert api.get(status_url(token)).data == {"status": "pending"}
    verification.resolve_contact(token, "+998901234567", 7, "Ali")
    assert api.get(status_url(token)).data == {"status": "verified"}
    assert api.get(status_url("yoq-token")).data == {"status": "expired"}


def test_auth_contact_verifies_and_stores_phone(db, fake_redis):
    token = new_token()
    outcome, _, shared = verification.resolve_contact(token, "998901234567", 7, "Ali Valiyev")
    assert outcome == "verified"
    assert shared == "+998901234567"
    session = verification.get_session(token)
    assert session["phone"] == "+998901234567"
    assert session["full_name"] == "Ali Valiyev"
    assert session["telegram_id"] == 7
    assert verification.status_of(token) == "verified"


def test_auth_contact_foreign(db, fake_redis):
    token = new_token()
    assert verification.resolve_contact(token, "+79001234567", 7, "Ivan")[0] == "foreign"
    assert verification.status_of(token) == "mismatch"
    assert verification.get_session(token)["phone"] is None


def test_consume_auth_once(db, fake_redis):
    pending = new_token()
    assert verification.consume_auth(pending) is None

    token = new_token()
    verification.resolve_contact(token, "+998901234567", 7, "Ali")
    session = verification.consume_auth(token)
    assert session["phone"] == "+998901234567"
    assert verification.consume_auth(token) is None


def test_consume_auth_rejects_mismatch(db, fake_redis):
    token = new_token()
    verification.resolve_contact(token, "+79001234567", 7, "Ivan")
    assert verification.consume_auth(token) is None


def test_mask_phone():
    assert verification.mask_phone("+998901234567") == "+998 90 ***-45-67"


def test_resolve_contact_expired(db, fake_redis):
    assert verification.resolve_contact("yoq-token", "+998901234567", 7) == (
        "expired", None, None)


def test_chat_binding(db, fake_redis):
    token = new_token()
    verification.bind_chat(7, token)
    assert verification.chat_token(7) == token
    verification.unbind_chat(7)
    assert verification.chat_token(7) is None
