"""Ro'yxatdan o'tish Telegram tasdig'i bilan, mehmonni aylantirish, parol tiklash."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import Device, User
from apps.billing.models import Student
from apps.progress.models import SavedQuestion
from apps.telegramauth import verification

REGISTER = "/api/v1/auth/register/"
PHONE = "+998901234567"
UPDATE_REQUIRED = {"code": "update_required", "detail": "Ilovaning yangi versiyasini o'rnating."}


def verified(phone=PHONE, purpose="register"):
    token = verification.start_session(phone, purpose, "uz")
    verification.mark(token, verification.Status.VERIFIED, telegram_id=7)
    return token


def register(api, **extra):
    body = {"phone": PHONE, "password": "parol123", "full_name": "Ali Valiyev", **extra}
    return api.post(REGISTER, body, format="json")


def make_guest(api):
    r = api.post("/api/v1/auth/guest/", {"device_id": "a" * 32}, format="json")
    return r.data


def test_register_requires_verification(api, db):
    r = register(api)
    assert r.status_code == 400
    assert r.data == UPDATE_REQUIRED


def test_register_with_verified_token(api, db, fake_redis):
    r = register(api, verification=verified())
    assert r.status_code == 201, r.data
    user = User.objects.get(phone=PHONE)
    assert user.role == "student" and user.pro_active


def test_register_wrong_phone_token(api, db, fake_redis):
    r = register(api, verification=verified("+998911112233"))
    assert r.status_code == 400
    assert r.data["code"] == "verification_invalid"


def test_verification_token_single_use(api, db, fake_redis):
    token = verified()
    assert register(api, verification=token).status_code == 201
    User.objects.filter(phone=PHONE).delete()
    r = register(api, verification=token)
    assert r.status_code == 400
    assert r.data["code"] == "verification_invalid"


def test_guest_converts_keeps_progress(api, db, fake_redis, question):
    guest = make_guest(api)
    guest_user = User.objects.get(pk=guest["user"]["id"])
    SavedQuestion.objects.create(user=guest_user, question=question)

    r = register(api, verification=verified(), guest_refresh=guest["tokens"]["refresh"])

    assert r.status_code == 201, r.data
    assert r.data["user"]["id"] == guest_user.pk
    guest_user.refresh_from_db()
    assert guest_user.role == "student" and guest_user.phone == PHONE
    assert guest_user.check_password("parol123")
    assert SavedQuestion.objects.filter(user=guest_user).exists()
    assert not Device.objects.filter(user=guest_user, refresh_jti__isnull=False,
                                     expires_at__isnull=False, is_active=True).exists()


def test_expired_guest_converts_with_refresh(api, db, fake_redis):
    guest = make_guest(api)
    Device.objects.filter(user_id=guest["user"]["id"]).update(
        expires_at=timezone.now() - timedelta(days=3), is_active=False)

    r = register(api, verification=verified(), guest_refresh=guest["tokens"]["refresh"])

    assert r.status_code == 201, r.data
    assert r.data["user"]["id"] == guest["user"]["id"]


def test_guest_refresh_of_student_ignored(api, student, fake_redis):
    login = api.post("/api/v1/auth/login/",
                     {"phone": student.phone, "password": "pass1234"}, format="json")
    r = register(api, verification=verified(), guest_refresh=login.data["tokens"]["refresh"])
    assert r.status_code == 201
    assert r.data["user"]["id"] != student.pk
    student.refresh_from_db()
    assert student.phone == "+998901110001"


def test_flag_off_allows_old_register(api, db, settings):
    settings.REGISTER_REQUIRE_TELEGRAM = False
    assert register(api).status_code == 201


def test_send_code_register_update_required(api, db, fake_redis):
    r = api.post("/api/v1/auth/send-code/", {"phone": PHONE, "purpose": "register"}, format="json")
    assert r.status_code == 400
    assert r.data == UPDATE_REQUIRED
    r = api.post("/api/v1/auth/send-code/", {"phone": PHONE, "purpose": "reset"}, format="json")
    assert r.data.get("code") != "update_required"


def test_reset_with_telegram_token(api, student, fake_redis):
    token = verified(student.phone, "reset")
    r = api.post("/api/v1/auth/reset-password/",
                 {"phone": student.phone, "token": token, "password": "yangi123"}, format="json")
    assert r.status_code == 204
    login = api.post("/api/v1/auth/login/",
                     {"phone": student.phone, "password": "yangi123"}, format="json")
    assert login.status_code == 200


def test_student_reset_switches_to_own_password(api, db, fake_redis):
    Student.objects.create(name="Talaba", phone=PHONE, password="1234")
    token = verified(PHONE, "reset")
    r = api.post("/api/v1/auth/reset-password/",
                 {"phone": PHONE, "token": token, "password": "yangi123"}, format="json")
    assert r.status_code == 204

    ok = api.post("/api/v1/auth/login/", {"phone": PHONE, "password": "yangi123"}, format="json")
    old = api.post("/api/v1/auth/login/", {"phone": PHONE, "password": "1234"}, format="json")
    assert ok.status_code == 200 and old.status_code == 400
    assert Student.objects.get(phone=PHONE).password == ""
    user = User.objects.get(phone=PHONE)
    assert user.has_usable_password() and not user.check_password("")
