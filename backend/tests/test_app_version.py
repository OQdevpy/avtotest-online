"""Majburiy yangilash: `app/version/` va foydalanuvchi versiyalari statistikasi."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import Device
from apps.releases.models import STORE_URLS, AppRelease, UserAppVersion, parse_version

pytestmark = pytest.mark.django_db

URL = "/api/v1/app/version/"


def check(api, platform="android", version="1.2.0"):
    return api.get(URL, {"platform": platform, "version": version})


@pytest.fixture
def android():
    return AppRelease.objects.create(platform="android", min_version="1.2.0",
                                     latest_version="1.3.0")


@pytest.mark.parametrize("raw,expected", [
    ("1.2.0", (1, 2, 0)), ("1.2", (1, 2, 0)), ("10.0.1", (10, 0, 1)),
    ("", None), ("1.2.x", None), ("v1.2", None),
])
def test_parse_version(raw, expected):
    assert parse_version(raw) == expected


@pytest.mark.parametrize("version,required,available", [
    ("1.1.0", True, True),     # minimaldan past — majburiy
    ("1.2.0", False, True),    # minimal, lekin oxirgisi emas — taklif
    ("1.2", False, True),      # 1.2 == 1.2.0
    ("1.3.0", False, False),   # eng oxirgisi
    ("1.10.0", False, False),  # raqam bo'yicha, matn bo'yicha emas
])
def test_update_flags(api, android, version, required, available):
    data = check(api, version=version).json()
    assert data["update_required"] is required
    assert data["update_available"] is available
    assert data["store_url"] == STORE_URLS["android"]


def test_missing_or_bad_version_is_never_blocked(api, android):
    for version in ("", "abc"):
        data = check(api, version=version).json()
        assert data["update_required"] is False


def test_no_release_configured(api):
    data = check(api, platform="ios", version="1.0.0").json()
    assert data["update_required"] is False and data["update_available"] is False
    assert data["store_url"] == STORE_URLS["ios"]


def test_bad_platform(api):
    assert check(api, platform="windows").status_code == 400


def test_custom_store_url(api):
    AppRelease.objects.create(platform="ios", store_url="https://apps.apple.com/app/id1")
    assert check(api, platform="ios").json()["store_url"] == "https://apps.apple.com/app/id1"


def test_records_version_of_logged_in_user(api, student, auth):
    auth(api, student)
    check(api, version="1.2.0")
    check(api, version="1.2.1")
    row = UserAppVersion.objects.get(user=student)
    assert (row.platform, row.version) == ("android", "1.2.1")


def test_anonymous_and_bad_token_are_fine(api):
    assert check(api).status_code == 200
    api.credentials(HTTP_AUTHORIZATION="Bearer notatoken")
    assert check(api).status_code == 200
    assert not UserAppVersion.objects.exists()


def test_invalid_version_not_recorded(api, student, auth):
    auth(api, student)
    check(api, version="abc")
    assert not UserAppVersion.objects.exists()


def test_release_validation():
    from django.core.exceptions import ValidationError

    with pytest.raises(ValidationError):
        AppRelease(platform="android", min_version="1.2.x").full_clean()


def test_admin_stats(client, django_user_model, student, settings):
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    admin = django_user_model.objects.create_superuser("+998901119998", "Admin12345")
    client.force_login(admin)
    UserAppVersion.objects.create(user=student, platform="android", version="1.2.0")
    old_user = django_user_model.objects.create_user("+998901119997", "x1234567")
    Device.objects.create(user=old_user, platform="mobile", refresh_jti="j1")
    Device.objects.filter(user=old_user).update(last_seen=timezone.now() - timedelta(days=1))

    body = client.get("/admin/releases/userappversion/").content.decode()
    assert "android 1.2.0: 1" in body
    assert "Versiya yubormaydigan eski ilovada: 1" in body
