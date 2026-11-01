"""Mehmon rejimi — ro'yxatdan o'tmasdan 5 kun (`POST /auth/guest/`)."""

from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.models import AccessCode, Device, User

GUEST_URL = "/api/v1/auth/guest/"


def make_guest(api, device_id="a" * 32):
    r = api.post(GUEST_URL, {"device_id": device_id, "lang": "uz"}, format="json")
    assert r.status_code == 201, r.data
    return r


def use(api, r):
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['tokens']['access']}")
    return api


def expire(user):
    Device.objects.filter(user=user).update(expires_at=timezone.now() - timedelta(minutes=1))


def test_guest_creates_session(api, db):
    r = make_guest(api)
    assert r.data["user"]["role"] == "guest"
    assert r.data["tokens"]["access"] and r.data["tokens"]["refresh"]
    assert r.data["guest_until"]
    user = User.objects.get(pk=r.data["user"]["id"])
    assert not user.phone.startswith("+998") and len(user.phone) <= 13
    assert not user.has_usable_password()
    device = user.devices.get()
    assert device.platform == "mobile" and device.machine_id == "a" * 32
    assert round((device.expires_at - device.created_at).total_seconds() / 86400) == 5


def test_two_guests_get_distinct_phones(api, db):
    first = make_guest(api).data["user"]["phone"]
    second = make_guest(api, "b" * 32).data["user"]["phone"]
    assert first != second


def test_guest_reads_content(api, db, ticket):
    use(api, make_guest(api))
    assert api.get("/api/v1/tickets/").status_code == 200


def test_guest_is_not_pro(api, db):
    use(api, make_guest(api))
    assert api.get("/api/v1/auth/me/").data["pro_active"] is False


def test_expired_guest_gets_guest_expired(api, db):
    r = make_guest(api)
    expire(User.objects.get(pk=r.data["user"]["id"]))
    res = use(api, r).get("/api/v1/tickets/")
    assert res.status_code == 401
    assert res.data["code"] == "guest_expired"


def test_closed_code_session_still_session_closed(api, student):
    code = AccessCode.generate(user=student)
    r = api.post("/api/v1/auth/login-code/",
                 {"code": code.code, "device_id": "c" * 32}, format="json")
    assert r.status_code == 200
    code.refresh_from_db()
    code.revoke()
    res = use(api, r).get("/api/v1/tickets/")
    assert res.status_code == 401
    assert res.data["code"] == "session_closed"


def test_guest_cannot_change_password(api, db):
    use(api, make_guest(api))
    res = api.post("/api/v1/auth/change-password/",
                   {"old_password": "x", "new_password": "yangi123"}, format="json")
    assert res.status_code == 403


def test_guest_throttled(api, db, monkeypatch):
    from rest_framework.throttling import SimpleRateThrottle

    monkeypatch.setattr(SimpleRateThrottle, "THROTTLE_RATES", {"guest": "2/hour"})
    make_guest(api)
    make_guest(api)
    res = api.post(GUEST_URL, {"device_id": "d" * 32}, format="json")
    assert res.status_code == 429


def test_prune_deletes_old_guests(api, db, student):
    old = User.objects.get(pk=make_guest(api).data["user"]["id"])
    recent = User.objects.get(pk=make_guest(api, "e" * 32).data["user"]["id"])
    User.objects.filter(pk=old.pk).update(date_joined=timezone.now() - timedelta(days=36))
    User.objects.filter(pk=recent.pk).update(date_joined=timezone.now() - timedelta(days=10))

    call_command("prune_devices")

    assert not User.objects.filter(pk=old.pk).exists()
    assert User.objects.filter(pk=recent.pk).exists()
    assert User.objects.filter(pk=student.pk).exists()
