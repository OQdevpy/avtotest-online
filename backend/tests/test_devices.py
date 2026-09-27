from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import Device

pytestmark = pytest.mark.django_db

PASSWORD = "pass1234"


def login(api, user, platform="mobile", label=""):
    body = {"phone": user.phone, "password": PASSWORD, "platform": platform}
    if label:
        body["device_label"] = label
    response = api.post("/api/v1/auth/login/", body, format="json")
    return response


def test_login_creates_device(api, student):
    response = login(api, student, platform="web")
    assert response.status_code == 200
    assert Device.objects.filter(user=student, platform="web").count() == 1


def test_login_records_device_label(api, student):
    login(api, student, platform="web", label="Chrome / Windows")
    assert Device.objects.get(user=student).label == "Chrome / Windows"


def test_default_platform_is_mobile(api, student):
    api.post("/api/v1/auth/login/",
             {"phone": student.phone, "password": PASSWORD}, format="json")
    assert Device.objects.get(user=student).platform == "mobile"


def test_second_web_login_is_rejected(api, student):
    assert login(api, student, platform="web").status_code == 200
    response = login(api, student, platform="web")
    assert response.status_code == 403
    assert "qurilma" in response.json()["detail"].lower()


def test_mobile_allows_two_devices(api, student):
    assert login(api, student, platform="mobile").status_code == 200
    assert login(api, student, platform="mobile").status_code == 200
    assert Device.objects.filter(user=student, platform="mobile").count() == 2


def test_third_mobile_login_is_rejected(api, student):
    login(api, student, platform="mobile")
    login(api, student, platform="mobile")
    assert login(api, student, platform="mobile").status_code == 403


def test_platforms_have_independent_limits(api, student):
    assert login(api, student, platform="web").status_code == 200
    assert login(api, student, platform="mobile").status_code == 200


def test_user_max_devices_overrides_platform_default(api, student):
    student.max_devices = 3
    student.save(update_fields=["max_devices"])
    for _ in range(3):
        assert login(api, student, platform="web").status_code == 200
    assert login(api, student, platform="web").status_code == 403


def test_mobile_device_has_no_expiry(api, student):
    login(api, student, platform="mobile")
    assert Device.objects.get(user=student).expires_at is None


def test_web_device_expires_in_twelve_days(api, student):
    login(api, student, platform="web")
    device = Device.objects.get(user=student)
    assert device.expires_at is not None
    days = (device.expires_at - device.created_at).total_seconds() / 86400
    assert 11.9 < days < 12.1


def test_refresh_rotates_and_keeps_device(api, student):
    refresh = login(api, student, platform="web").json()["tokens"]["refresh"]
    response = api.post("/api/v1/auth/token/refresh/", {"refresh": refresh}, format="json")
    assert response.status_code == 200
    assert Device.objects.filter(user=student, is_active=True).count() == 1


# Review Focus #4
def test_refresh_fails_after_device_expires(api, student):
    refresh = login(api, student, platform="web").json()["tokens"]["refresh"]
    Device.objects.filter(user=student).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    response = api.post("/api/v1/auth/token/refresh/", {"refresh": refresh}, format="json")
    assert response.status_code == 401


def test_refresh_fails_for_deactivated_device(api, student):
    refresh = login(api, student, platform="web").json()["tokens"]["refresh"]
    Device.objects.filter(user=student).update(is_active=False)
    response = api.post("/api/v1/auth/token/refresh/", {"refresh": refresh}, format="json")
    assert response.status_code == 401


def test_logout_deactivates_device_and_blocks_refresh(api, student, auth):
    tokens = login(api, student, platform="web").json()["tokens"]
    auth(api, student)
    assert api.post("/api/v1/auth/logout/",
                    {"refresh": tokens["refresh"]}, format="json").status_code == 204
    assert not Device.objects.get(user=student).is_active
    assert api.post("/api/v1/auth/token/refresh/",
                    {"refresh": tokens["refresh"]}, format="json").status_code == 401


def test_logout_frees_the_device_slot(api, student, auth):
    tokens = login(api, student, platform="web").json()["tokens"]
    auth(api, student)
    api.post("/api/v1/auth/logout/", {"refresh": tokens["refresh"]}, format="json")
    api.credentials()
    assert login(api, student, platform="web").status_code == 200


def test_devices_list_shows_own_devices_only(api, student, other_student, auth):
    login(api, student, platform="web")
    login(api, other_student, platform="web")
    auth(api, student)
    body = api.get("/api/v1/auth/devices/").json()
    rows = body["results"] if isinstance(body, dict) else body
    assert len(rows) == 1
    assert rows[0]["platform"] == "web"


def test_device_can_be_deleted_by_owner(api, student, auth):
    login(api, student, platform="web")
    device = Device.objects.get(user=student)
    auth(api, student)
    assert api.delete(f"/api/v1/auth/devices/{device.id}/").status_code == 204
    assert not Device.objects.get(pk=device.pk).is_active


def test_cannot_delete_another_users_device(api, student, other_student, auth):
    login(api, other_student, platform="web")
    device = Device.objects.get(user=other_student)
    auth(api, student)
    assert api.delete(f"/api/v1/auth/devices/{device.id}/").status_code == 404


def test_prune_devices_deactivates_expired(api, student):
    from django.core.management import call_command

    login(api, student, platform="web")
    Device.objects.filter(user=student).update(
        expires_at=timezone.now() - timedelta(days=1)
    )
    call_command("prune_devices")
    assert not Device.objects.get(user=student).is_active
