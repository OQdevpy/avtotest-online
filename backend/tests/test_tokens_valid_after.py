"""Eski avtotest backend'i chiqargan tokenlar boshqa odamning hisobini ochmasin.

Ikki baza ajralgandan keyin bir xil `id` ikkala tomonda boshqa-boshqa odamga
berilgan. Kalit (SECRET_KEY) bir xil, shuning uchun eski tokenni rad etish uchun
`User.tokens_valid_after` dan oldin chiqarilgan tokenlar qabul qilinmaydi.
"""

from datetime import timedelta

from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import AccessCode, Device

ME = "/api/v1/auth/me/"
REFRESH = "/api/v1/auth/token/refresh/"


def bearer(api, token):
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api


def test_access_token_before_cutoff_rejected(api, student):
    refresh = RefreshToken.for_user(student)
    student.tokens_valid_after = timezone.now() + timedelta(seconds=5)
    student.save(update_fields=["tokens_valid_after"])
    res = bearer(api, str(refresh.access_token)).get(ME)
    assert res.status_code == 401
    assert res.data["code"] == "session_closed"


def test_access_token_after_cutoff_ok(api, student):
    student.tokens_valid_after = timezone.now() - timedelta(minutes=1)
    student.save(update_fields=["tokens_valid_after"])
    refresh = RefreshToken.for_user(student)
    assert bearer(api, str(refresh.access_token)).get(ME).status_code == 200


def test_refresh_before_cutoff_rejected_and_no_device_created(api, student):
    refresh = RefreshToken.for_user(student)  # Device yozuvisiz — eski bazadan kelgandek
    student.tokens_valid_after = timezone.now() + timedelta(seconds=5)
    student.save(update_fields=["tokens_valid_after"])
    res = api.post(REFRESH, {"refresh": str(refresh)}, format="json")
    assert res.status_code == 401
    assert not Device.objects.filter(user=student).exists()


def test_code_session_of_other_user_rejected(api, student, other_student):
    code = AccessCode.generate(user=other_student)
    r = api.post("/api/v1/auth/login-code/", {"code": code.code, "device_id": "f" * 32},
                 format="json")
    assert r.status_code == 200
    did = RefreshToken(r.data["tokens"]["refresh"])["did"]
    # Boshqa bazadan kelgan token: did shu yerdagi boshqa odamning qurilmasi
    forged = RefreshToken.for_user(student)
    forged["did"] = did
    api.credentials()
    res = bearer(api, str(forged.access_token)).get(ME)
    assert res.status_code == 401
