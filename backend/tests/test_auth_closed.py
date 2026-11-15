"""Parol, ijtimoiy kirish va OTP yo'llari yopilgan — eski ilova yangilanishga yo'naltiriladi."""

import pytest

UPDATE_REQUIRED = {"code": "update_required", "detail": "Ilovaning yangi versiyasini o'rnating."}

CLOSED = [
    ("/api/v1/auth/login/", {"phone": "+998901110001", "password": "pass1234"}),
    ("/api/v1/auth/register/", {"phone": "+998901234567", "password": "parol123"}),
    ("/api/v1/auth/social/", {"provider": "google", "uid": "1", "token": "x"}),
    ("/api/v1/auth/change-password/", {"old_password": "pass1234", "new_password": "yangi123"}),
    ("/api/v1/auth/send-code/", {"phone": "+998901110001", "purpose": "reset"}),
    ("/api/v1/auth/verify-code/", {"phone": "+998901110001", "purpose": "reset", "code": "123456"}),
    ("/api/v1/auth/reset-password/",
     {"phone": "+998901110001", "token": "x", "password": "yangi123"}),
]


@pytest.mark.parametrize("url,body", CLOSED)
def test_closed_without_token(api, student, url, body):
    r = api.post(url, body, format="json")
    assert r.status_code == 400
    assert r.data == UPDATE_REQUIRED


@pytest.mark.parametrize("url,body", CLOSED)
def test_closed_with_token(api, auth, student, url, body):
    r = auth(api, student).post(url, body, format="json")
    assert r.status_code == 400
    assert r.data == UPDATE_REQUIRED


def test_password_not_changed(api, auth, student):
    auth(api, student).post("/api/v1/auth/change-password/",
                            {"old_password": "pass1234", "new_password": "yangi123"},
                            format="json")
    student.refresh_from_db()
    assert student.check_password("pass1234")
