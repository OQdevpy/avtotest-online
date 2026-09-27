"""Tekshiruvda topilgan xatolar uchun regressiya testlari."""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Device

pytestmark = pytest.mark.django_db

GOOGLE_CLIENT = "123.apps.googleusercontent.com"


@pytest.fixture
def google_ok(settings, monkeypatch):
    """Google tekshiruvi 'g-attacker' uid'i uchun muvaffaqiyatli o'tadi."""
    from apps.accounts import social

    settings.GOOGLE_CLIENT_IDS = [GOOGLE_CLIENT]

    class Response:
        status_code = 200

        def json(self):
            return {"aud": GOOGLE_CLIENT, "sub": "g-attacker", "email": "a@b.c"}

    monkeypatch.setattr(social, "_http_get", lambda url, **kw: Response())


# --- Critical #1: hisob o'g'irlash ------------------------------------------

def test_social_login_cannot_claim_existing_account_by_phone(api, student, google_ok):
    """Mijoz yuborgan telefon bilan begona hisobga kirib bo'lmaydi."""
    response = api.post("/api/v1/auth/social/", {
        "provider": "google", "token": "ok", "uid": "g-attacker",
        "phone": student.phone,
    }, format="json")
    assert response.status_code != 200 or response.json()["user"]["id"] != student.id
    if response.status_code in (200, 201):
        # Yangi hisob yaratilgan bo'lishi kerak, jabrlanuvchining hisobi emas.
        assert response.json()["user"]["id"] != student.id
    assert not student.social_accounts.exists()


def test_social_login_reuses_account_only_via_verified_uid(api, google_ok):
    """Ikkinchi kirish o'sha uid bo'yicha o'sha hisobga tushadi."""
    first = api.post("/api/v1/auth/social/", {
        "provider": "google", "token": "ok", "uid": "g-attacker",
    }, format="json")
    assert first.status_code == 201
    user_id = first.json()["user"]["id"]

    Device.objects.filter(user_id=user_id).update(is_active=False)
    second = api.post("/api/v1/auth/social/", {
        "provider": "google", "token": "ok", "uid": "g-attacker",
    }, format="json")
    assert second.status_code == 200
    assert second.json()["user"]["id"] == user_id


# --- Critical #2: do'kondagi ilovaning o'rganish ekrani ---------------------

def test_lesson_detail_keeps_answer_key_for_shipped_client(api, student, auth, question):
    """Mobil ilova lessons/{id}/ ni ?mode=study SIZ chaqiradi va kalitni kutadi."""
    auth(api, student)
    body = api.get(f"/api/v1/lessons/{question.lesson_id}/").json()
    answer = body["questions"][0]["answers"][0]
    assert "is_true" in answer


def test_lesson_detail_keeps_explanation_and_media_fields(api, student, auth, question):
    auth(api, student)
    body = api.get(f"/api/v1/lessons/{question.lesson_id}/").json()
    row = body["questions"][0]
    for field in ("explanation", "audio_url", "explanation_image_url"):
        assert field in row


def test_ticket_detail_still_hides_answer_key(api, student, auth, ticket):
    """Bilet — test rejimi, u yerda kalit yopiq qoladi."""
    auth(api, student)
    body = api.get(f"/api/v1/tickets/{ticket.number}/").json()
    assert "is_true" not in body["questions"][0]["answers"][0]


# --- Critical #3: jonli sessiyalar uzilmasligi ------------------------------

def test_refresh_grandfathers_session_without_device(api, student):
    """Bazadan tiklangan sessiyada Device yo'q — u chiqarib tashlanmasligi kerak."""
    refresh = str(RefreshToken.for_user(student))
    assert not Device.objects.filter(user=student).exists()
    response = api.post("/api/v1/auth/token/refresh/", {"refresh": refresh}, format="json")
    assert response.status_code == 200
    assert Device.objects.filter(user=student).count() == 1


def test_grandfathered_device_gets_default_platform_and_expiry(api, student):
    refresh = str(RefreshToken.for_user(student))
    api.post("/api/v1/auth/token/refresh/", {"refresh": refresh}, format="json")
    device = Device.objects.get(user=student)
    assert device.platform == "mobile"
    assert device.expires_at is None


def test_expired_device_is_still_rejected(api, student):
    """Grandfathering Focus #4 ni buzmasligi kerak."""
    login = api.post("/api/v1/auth/login/", {
        "phone": student.phone, "password": "pass1234", "platform": "web",
    }, format="json")
    refresh = login.json()["tokens"]["refresh"]
    Device.objects.filter(user=student).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    response = api.post("/api/v1/auth/token/refresh/", {"refresh": refresh}, format="json")
    assert response.status_code == 401


def test_deactivated_device_is_still_rejected(api, student):
    login = api.post("/api/v1/auth/login/", {
        "phone": student.phone, "password": "pass1234", "platform": "web",
    }, format="json")
    refresh = login.json()["tokens"]["refresh"]
    Device.objects.filter(user=student).update(is_active=False)
    response = api.post("/api/v1/auth/token/refresh/", {"refresh": refresh}, format="json")
    assert response.status_code == 401
