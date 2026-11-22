"""Push qurilma tokenlari: ro'yxatdan o'tkazish va o'chirish (mehmon ham)."""

import pytest

from apps.notifications.models import PushDevice

pytestmark = pytest.mark.django_db

REG = "/api/v1/notifications/devices/"
REMOVE = "/api/v1/notifications/devices/remove/"
TOKEN = "fcm-token-" + "x" * 140


def register(api, token=TOKEN, platform="android", **extra):
    return api.post(REG, {"token": token, "platform": platform, **extra}, format="json")


def test_register_creates_device(api, auth, student):
    auth(api, student)
    r = register(api, app_version="1.3.0")
    assert r.status_code == 200, r.data
    d = PushDevice.objects.get()
    assert (d.user, d.token, d.platform, d.app_version, d.is_active) == (
        student, TOKEN, "android", "1.3.0", True)


def test_register_same_token_idempotent(api, auth, student):
    auth(api, student)
    register(api)
    PushDevice.objects.update(is_active=False, last_error="UNREGISTERED")
    register(api, platform="ios")
    d = PushDevice.objects.get()
    assert d.is_active and d.platform == "ios" and d.last_error == ""


def test_register_moves_token_to_new_owner(api, auth, student, other_student):
    auth(api, student)
    register(api)
    auth(api, other_student)
    register(api)
    assert PushDevice.objects.count() == 1
    assert PushDevice.objects.get().user == other_student


def test_guest_can_register(api):
    r = api.post("/api/v1/auth/guest/", {"device_id": "g" * 32, "lang": "ru"}, format="json")
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['tokens']['access']}")
    assert register(api, platform="ios").status_code == 200
    assert PushDevice.objects.get().user.role == "guest"


def test_remove_only_own_token(api, auth, student, other_student):
    PushDevice.objects.create(user=other_student, token="other", platform="android")
    auth(api, student)
    register(api)
    assert api.post(REMOVE, {"token": "other"}, format="json").status_code == 200
    assert api.post(REMOVE, {"token": TOKEN}, format="json").status_code == 200
    assert list(PushDevice.objects.values_list("token", flat=True)) == ["other"]


def test_register_requires_auth(api):
    assert register(api).status_code == 401


def test_bad_platform_400(api, auth, student):
    auth(api, student)
    assert register(api, platform="windows").status_code == 400
    assert register(api, token="").status_code == 400
