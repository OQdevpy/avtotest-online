"""Telegram orqali raqamni tasdiqlash — sessiya, start/status va bot mantig'i."""

import re

import pytest

from apps.telegramauth import verification

START = "/api/v1/auth/telegram/start/"


def status_url(token):
    return f"/api/v1/auth/telegram/status/{token}/"


def start(api, phone="901234567", purpose="register"):
    return api.post(START, {"phone": phone, "purpose": purpose, "lang": "uz"}, format="json")


def test_start_returns_link(api, db, fake_redis):
    r = start(api)
    assert r.status_code == 200, r.data
    assert r.data["link"] == f"https://t.me/AvtotestTayyorlovBot?start={r.data['token']}"
    assert re.fullmatch(r"[A-Za-z0-9_-]{1,64}", r.data["token"])
    assert r.data["expires_in"] == 600


def test_status_flow(api, db, fake_redis):
    token = start(api).data["token"]
    assert api.get(status_url(token)).data == {"status": "pending"}
    verification.mark(token, verification.Status.VERIFIED, telegram_id=7)
    assert api.get(status_url(token)).data == {"status": "verified"}
    assert api.get(status_url("yoq-token")).data == {"status": "expired"}


def test_register_phone_taken(api, student, fake_redis):
    r = start(api, phone=student.phone)
    assert r.status_code == 400
    assert r.data["code"] == "phone_taken"


def test_guest_phone_not_taken(api, db, fake_redis):
    api.post("/api/v1/auth/guest/", {"device_id": "a" * 32}, format="json")
    assert start(api).status_code == 200


def test_reset_no_user(api, db, fake_redis):
    r = start(api, purpose="reset")
    assert r.status_code == 404
    assert r.data["code"] == "no_user"


def test_too_many_sessions(api, db, fake_redis):
    for _ in range(5):
        assert start(api).status_code == 200
    r = start(api)
    assert r.status_code == 429
    assert r.data["code"] == "too_many"


def test_consume_only_verified(db, fake_redis):
    token = verification.start_session("+998901234567", "register", "uz")
    assert verification.consume(token, "+998901234567", "register") is False
    verification.mark(token, verification.Status.VERIFIED, telegram_id=7)
    assert verification.consume(token, "+998911112233", "register") is False
    assert verification.consume(token, "+998901234567", "reset") is False
    assert verification.consume(token, "+998901234567", "register") is True
    assert verification.consume(token, "+998901234567", "register") is False
