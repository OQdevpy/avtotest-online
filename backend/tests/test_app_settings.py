"""Ilova sozlamalari (admin): mehmon kunlari, bepul PRO, to'lov oynasi, yopiq bo'limlar."""

from datetime import timedelta

from django.utils import timezone

from apps.accounts.models import User
from apps.releases.models import AppSettings
from apps.telegramauth import verification

CLAIM = "/api/v1/auth/telegram/claim/"
PHONE = "+998901112233"


def verified_token(phone=PHONE):
    token = verification.start_session(None, "auth", "uz", ip="10.0.0.9")
    verification.resolve_contact(token, phone, 77, "Yangi O'quvchi")
    return token


def test_config_defaults_match_current_behaviour(api, db):
    r = api.get("/api/v1/app/config/?platform=android")
    assert r.status_code == 200
    assert r.json() == {"guest_days": 3, "welcome_pro_days": 12, "paywall_after_signup": False,
                        "locked_sections": ["topics", "exam", "hard"], "review_login": False}


def test_config_from_admin_values(api, db):
    AppSettings(guest_days=1, welcome_pro_days=0, paywall_after_signup=True,
                locked_sections=["topics", "exam", "tickets", "bogus"]).save()
    data = api.get("/api/v1/app/config/").json()
    assert data["guest_days"] == 1 and data["welcome_pro_days"] == 0
    assert data["paywall_after_signup"] is True
    assert data["locked_sections"] == ["topics", "exam", "tickets"]  # noma'lumi tashlanadi
    assert AppSettings.objects.count() == 1


def test_signup_default_gives_welcome_pro(api, db, fake_redis):
    r = api.post(CLAIM, {"token": verified_token()}, format="json")
    assert r.status_code == 201 and r.data["show_paywall"] is False
    user = User.objects.get(phone=PHONE)
    assert user.pro_active and user.pro_until > timezone.now() + timedelta(days=11)


def test_signup_without_gift_shows_paywall(api, db, fake_redis):
    AppSettings(welcome_pro_days=0, paywall_after_signup=True).save()
    r = api.post(CLAIM, {"token": verified_token()}, format="json")
    assert r.status_code == 201
    assert r.data["show_paywall"] is True
    user = User.objects.get(phone=PHONE)
    assert not user.pro_active


def test_guest_turned_student_loses_trial_when_no_gift(api, db, fake_redis):
    AppSettings(welcome_pro_days=0, paywall_after_signup=True).save()
    guest = api.post("/api/v1/auth/guest/", {"device_id": "b" * 32}, format="json").data
    assert User.objects.get(pk=guest["user"]["id"]).pro_active  # mehmon sinovda
    r = api.post(CLAIM, {"token": verified_token(), "guest_refresh": guest["tokens"]["refresh"]},
                 format="json")
    assert r.status_code == 201 and r.data["show_paywall"] is True
    assert not User.objects.get(phone=PHONE).pro_active


def test_existing_user_login_never_shows_paywall(api, student, fake_redis):
    AppSettings(welcome_pro_days=0, paywall_after_signup=True).save()
    r = api.post(CLAIM, {"token": verified_token(student.phone)}, format="json")
    assert r.status_code == 200 and r.data["show_paywall"] is False


def test_guest_days_from_settings(api, db):
    AppSettings(guest_days=1).save()
    guest = api.post("/api/v1/auth/guest/", {"device_id": "c" * 32}, format="json").data
    device = User.objects.get(pk=guest["user"]["id"]).devices.get()
    assert timezone.now() + timedelta(hours=23) < device.expires_at < timezone.now() + timedelta(hours=25)


def test_legacy_pro_kept_when_no_gift(api, db, fake_redis, monkeypatch):
    from apps.telegramauth import legacy

    AppSettings(welcome_pro_days=0).save()
    until = timezone.now() + timedelta(days=40)
    monkeypatch.setattr(legacy, "legacy_user", lambda phone: {
        "full_name": "Eski", "language": "uz", "is_pro": True, "pro_until": until,
        "is_active": True, "date_joined": None})
    api.post(CLAIM, {"token": verified_token()}, format="json")
    user = User.objects.get(phone=PHONE)
    assert user.pro_active and user.pro_until == until


def test_guest_conversion_is_recorded_and_counted(api, db, fake_redis, client, django_user_model, settings):
    from apps.releases.admin import conversion_stats

    guest = api.post("/api/v1/auth/guest/", {"device_id": "d" * 32}, format="json").data
    api.post("/api/v1/auth/guest/", {"device_id": "e" * 32}, format="json")  # o'tmagan mehmon
    api.post(CLAIM, {"token": verified_token(), "guest_refresh": guest["tokens"]["refresh"]},
             format="json")
    api.post(CLAIM, {"token": verified_token("+998905556677")}, format="json")  # to'g'ridan-to'g'ri

    converted = User.objects.get(phone=PHONE)
    assert converted.guest_converted_at is not None
    assert User.objects.get(phone="+998905556677").guest_converted_at is None

    st = conversion_stats(7)
    assert (st["guests"], st["converted"], st["rate"], st["direct"], st["paid"]) == (2, 1, 50, 1, 0)

    settings.STORAGES = {**settings.STORAGES, "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}}
    client.force_login(django_user_model.objects.create_superuser(phone="+998900000881", password="x"))
    r = client.get("/admin/accounts/user/?from_guest=yes")
    assert r.status_code == 200 and PHONE in r.content.decode()
    assert "+998905556677" not in r.content.decode()
    AppSettings().save()
    r = client.get("/admin/releases/appsettings/1/change/")
    assert r.status_code == 200 and "Telegram" in r.content.decode()


def test_user_admin_shows_pro_until(db, client, django_user_model, settings):
    settings.STORAGES = {**settings.STORAGES, "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}}
    User.objects.create(phone="+998907770001", role="student", is_pro=True,
                        pro_until=timezone.now() + timedelta(days=10, hours=2))
    User.objects.create(phone="+998907770002", role="student", is_pro=True, pro_until=None)
    User.objects.create(phone="+998907770003", role="student", is_pro=True,
                        pro_until=timezone.now() - timedelta(days=1))
    client.force_login(django_user_model.objects.create_superuser(phone="+998900000882", password="x"))
    html = client.get("/admin/accounts/user/?o=-6").content.decode()
    assert "PRO muddati" in html
    assert "10 kun 1 soat qoldi" in html and "Muddatsiz" in html and "Tugagan" in html
