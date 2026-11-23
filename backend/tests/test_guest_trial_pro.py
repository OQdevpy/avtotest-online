"""Mehmon 3 kunlik sinovda hamma narsa ochiq (PRO kabi); muddat tugasa guest_expired."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import Device, User

pytestmark = pytest.mark.django_db
GUEST = "/api/v1/auth/guest/"


def guest(api):
    r = api.post(GUEST, {"device_id": "t" * 32, "lang": "uz"}, format="json")
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['tokens']['access']}")
    return User.objects.get(pk=r.data["user"]["id"])


def test_guest_has_full_access_in_trial(api):
    g = guest(api)
    me = api.get("/api/v1/auth/me/").json()
    assert me["pro_active"] is True
    assert g.pro_active is True
    # muddat — sinov tugashi (3 kun), "muddatsiz" emas
    until = timezone.datetime.fromisoformat(me["pro_until"].replace("Z", "+00:00"))
    assert timedelta(days=2, hours=23) < until - timezone.now() <= timedelta(days=3)
    # obuna emas — profil halqasi rangsiz
    assert me["pro_tier"] is None and me["pro_color"] is None


def test_guest_opens_pro_ticket(api):
    from apps.content.models import Ticket

    t = Ticket.objects.create(number=99, is_pro=True)
    guest(api)
    assert api.get(f"/api/v1/tickets/{t.number}/").status_code == 200


def test_student_without_pro_still_locked(api, auth, student):
    from apps.content.models import Ticket

    t = Ticket.objects.create(number=98, is_pro=True)
    auth(api, student)
    assert api.get("/api/v1/auth/me/").json()["pro_active"] is False
    assert api.get(f"/api/v1/tickets/{t.number}/").status_code == 403


def test_expired_guest_is_blocked(api):
    g = guest(api)
    Device.objects.filter(user=g).update(expires_at=timezone.now() - timedelta(minutes=1))
    r = api.get("/api/v1/auth/me/")
    assert r.status_code == 401 and r.json()["code"] == "guest_expired"
