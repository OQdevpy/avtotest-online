from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import AccessCode, Device

pytestmark = pytest.mark.django_db


def make_code(user, admin, **kwargs):
    return AccessCode.generate(user=user, created_by=admin, **kwargs)


def test_generated_code_is_eight_unambiguous_chars(student, admin_user):
    code = make_code(student, admin_user)
    assert len(code.code) == 8
    assert not set(code.code) & set("O0I1")


def test_generated_codes_are_unique(student, other_student, admin_user):
    assert make_code(student, admin_user).code != make_code(other_student, admin_user).code


def test_login_with_code_returns_tokens(api, student, admin_user):
    code = make_code(student, admin_user)
    response = api.post("/api/v1/auth/login-code/",
                        {"code": code.code, "platform": "desktop"}, format="json")
    assert response.status_code == 200
    assert "access" in response.json()["tokens"]
    assert response.json()["user"]["id"] == student.id


def test_login_with_code_activates_and_sets_expiry(api, student, admin_user):
    code = make_code(student, admin_user)
    api.post("/api/v1/auth/login-code/", {"code": code.code}, format="json")
    code.refresh_from_db()
    assert code.activated_at is not None
    days = (code.expires_at - code.activated_at).total_seconds() / 86400
    assert 11.9 < days < 12.1


def test_login_with_code_defaults_to_desktop_platform(api, student, admin_user):
    code = make_code(student, admin_user)
    api.post("/api/v1/auth/login-code/", {"code": code.code}, format="json")
    assert Device.objects.get(user=student).platform == "desktop"


def test_second_login_keeps_original_expiry(api, student, admin_user):
    code = make_code(student, admin_user)
    api.post("/api/v1/auth/login-code/", {"code": code.code}, format="json")
    code.refresh_from_db()
    first_expiry = code.expires_at
    Device.objects.filter(user=student).update(is_active=False)
    api.post("/api/v1/auth/login-code/", {"code": code.code}, format="json")
    code.refresh_from_db()
    assert code.expires_at == first_expiry


def test_revoked_code_rejected(api, student, admin_user):
    code = make_code(student, admin_user)
    code.is_active = False
    code.save(update_fields=["is_active"])
    assert api.post("/api/v1/auth/login-code/",
                    {"code": code.code}, format="json").status_code == 401


def test_expired_code_rejected(api, student, admin_user):
    code = make_code(student, admin_user)
    AccessCode.objects.filter(pk=code.pk).update(
        activated_at=timezone.now() - timedelta(days=20),
        expires_at=timezone.now() - timedelta(days=8),
    )
    assert api.post("/api/v1/auth/login-code/",
                    {"code": code.code}, format="json").status_code == 401


def test_code_for_inactive_user_rejected(api, student, admin_user):
    code = make_code(student, admin_user)
    student.is_active = False
    student.save(update_fields=["is_active"])
    assert api.post("/api/v1/auth/login-code/",
                    {"code": code.code}, format="json").status_code == 401


def test_unknown_code_rejected(api):
    assert api.post("/api/v1/auth/login-code/",
                    {"code": "ZZZZZZZZ"}, format="json").status_code == 401


def test_custom_valid_days_respected(api, student, admin_user):
    code = make_code(student, admin_user, valid_days=3)
    api.post("/api/v1/auth/login-code/", {"code": code.code}, format="json")
    code.refresh_from_db()
    days = (code.expires_at - code.activated_at).total_seconds() / 86400
    assert 2.9 < days < 3.1


def test_admin_creates_access_code(api, student, admin_user, auth):
    auth(api, admin_user)
    response = api.post("/api/v1/manage/access-codes/",
                        {"user": student.id}, format="json")
    assert response.status_code == 201
    assert len(response.json()["code"]) == 8


def test_student_cannot_create_access_code(api, student, auth):
    auth(api, student)
    assert api.post("/api/v1/manage/access-codes/",
                    {"user": student.id}, format="json").status_code == 403


def test_teacher_cannot_create_access_code(api, student, teacher, auth):
    auth(api, teacher)
    assert api.post("/api/v1/manage/access-codes/",
                    {"user": student.id}, format="json").status_code == 403


def test_admin_revokes_code(api, student, admin_user, auth):
    code = make_code(student, admin_user)
    auth(api, admin_user)
    assert api.post(f"/api/v1/manage/access-codes/{code.id}/revoke/").status_code == 200
    code.refresh_from_db()
    assert not code.is_active


def test_django_admin_generates_code_for_new_access_code(client, student, django_user_model):
    """Django admin'da `code` faqat o'qish uchun — kod avtomatik beriladi."""
    boss = django_user_model.objects.create_superuser(phone="+998900000777", password="x")
    client.force_login(boss)
    for _ in range(2):  # ikkinchisi ham (bo'sh kod unique xatosiga tushmasin)
        response = client.post(
            "/admin/accounts/accesscode/add/",
            {"user": student.pk, "valid_days": 12, "is_active": "on"},
        )
        assert response.status_code == 302, response.content[:500]

    codes = AccessCode.objects.filter(user=student)
    assert codes.count() == 2
    for code in codes:
        assert len(code.code) == AccessCode.LENGTH
        assert code.created_by == boss
