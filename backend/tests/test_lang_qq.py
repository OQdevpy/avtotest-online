"""Qoraqalpoq tili (`qq`) olib tashlandi — eski ilovadan kelgani `uz` deb o'qiladi."""

import importlib

from django.apps import apps as django_apps

from apps.accounts.models import User


def test_language_choices_no_qq():
    assert "qq" not in User.Language.values
    assert set(User.Language.values) == {"uz", "kr", "ru"}


def test_patch_language_qq_maps_to_uz(api, auth, student):
    r = auth(api, student).patch("/api/v1/auth/me/", {"language": "qq"}, format="json")
    assert r.status_code == 200, r.data
    assert r.data["language"] == "uz"
    student.refresh_from_db()
    assert student.language == "uz"


def test_patch_language_kr_still_works(api, auth, student):
    r = auth(api, student).patch("/api/v1/auth/me/", {"language": "kr"}, format="json")
    assert r.status_code == 200
    assert r.data["language"] == "kr"


def test_guest_lang_qq(api, db):
    r = api.post("/api/v1/auth/guest/", {"device_id": "a" * 32, "lang": "qq"}, format="json")
    assert r.status_code == 201, r.data
    assert r.data["user"]["language"] == "uz"


def test_content_lang_qq_is_uz(api, auth, student, question):
    auth(api, student)
    body = api.get(f"/api/v1/lessons/{question.lesson_id}/?lang=qq").json()
    assert body["questions"][0]["text"] == question.text_uz


def test_migration_moves_qq(db):
    User.objects.create_user("+998901112299", "x" * 8)
    User.objects.filter(phone="+998901112299").update(language="qq")
    module = importlib.import_module("apps.accounts.migrations.0008_language_qq_to_uz")
    module.qq_to_uz(django_apps, None)
    assert User.objects.get(phone="+998901112299").language == "uz"


def test_telegram_start_lang_qq_creates_uz_user(api, db, fake_redis):
    from apps.telegramauth import verification

    r = api.post("/api/v1/auth/telegram/start/", {"lang": "qq"}, format="json")
    assert r.status_code == 200, r.data
    token = r.data["token"]
    verification.resolve_contact(token, "+998901234567", 7, "Ali")
    res = api.post("/api/v1/auth/telegram/claim/", {"token": token}, format="json")
    assert res.status_code == 201, res.data
    assert res.data["user"]["language"] == "uz"
