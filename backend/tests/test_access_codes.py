from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import AccessCode, Device

pytestmark = pytest.mark.django_db

PC1 = "a" * 64
PC2 = "b" * 64


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
                        {"code": code.code, "platform": "desktop", "device_id": PC1}, format="json")
    assert response.status_code == 200
    assert "access" in response.json()["tokens"]
    assert response.json()["user"]["id"] == student.id


def test_code_session_never_expires(api, student, admin_user):
    code = make_code(student, admin_user)
    api.post("/api/v1/auth/login-code/", {"code": code.code, "device_id": PC1}, format="json")
    assert Device.objects.get(user=student).expires_at is None


def test_login_with_code_defaults_to_desktop_platform(api, student, admin_user):
    code = make_code(student, admin_user)
    api.post("/api/v1/auth/login-code/", {"code": code.code, "device_id": PC1}, format="json")
    assert Device.objects.get(user=student).platform == "desktop"


def test_revoked_code_rejected(api, student, admin_user):
    code = make_code(student, admin_user)
    code.is_active = False
    code.save(update_fields=["is_active"])
    assert api.post("/api/v1/auth/login-code/",
                    {"code": code.code, "device_id": PC1}, format="json").status_code == 401


def test_old_activated_code_still_works(api, student, admin_user):
    # Kod muddatsiz: eski activated_at/expires_at qiymatlari e'tiborga olinmaydi.
    code = make_code(student, admin_user)
    AccessCode.objects.filter(pk=code.pk).update(
        activated_at=timezone.now() - timedelta(days=20),
        expires_at=timezone.now() - timedelta(days=8),
    )
    assert api.post("/api/v1/auth/login-code/",
                    {"code": code.code, "device_id": PC1}, format="json").status_code == 200


def test_code_for_inactive_user_rejected(api, student, admin_user):
    code = make_code(student, admin_user)
    student.is_active = False
    student.save(update_fields=["is_active"])
    assert api.post("/api/v1/auth/login-code/",
                    {"code": code.code, "device_id": PC1}, format="json").status_code == 401


def test_unknown_code_rejected(api):
    assert api.post("/api/v1/auth/login-code/",
                    {"code": "ZZZZZZZZ", "device_id": PC1}, format="json").status_code == 401


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


# --- Bir kod — bir kompyuter ---------------------------------------------------

def login(api, code, device_id=PC1, platform="desktop"):
    payload = {"code": code.code, "platform": platform}
    if device_id is not None:
        payload["device_id"] = device_id
    return api.post("/api/v1/auth/login-code/", payload, format="json")


def test_first_login_binds_code_to_computer(api, student, admin_user):
    code = make_code(student, admin_user)
    assert login(api, code).status_code == 200
    code.refresh_from_db()
    assert code.device_id == PC1
    assert code.bound_at is not None
    assert Device.objects.get(user=student).machine_id == PC1


def test_same_computer_can_log_in_again(api, student, admin_user):
    code = make_code(student, admin_user)
    for _ in range(3):  # masalan, yangi versiya storage'ni tozalagach
        assert login(api, code).status_code == 200


def test_other_computer_is_rejected(api, student, admin_user):
    code = make_code(student, admin_user)
    login(api, code, PC1)
    response = login(api, code, PC2)
    assert response.status_code == 403
    assert "boshqa kompyuter" in response.json()["detail"]
    assert not Device.objects.filter(machine_id=PC2).exists()


def test_login_without_device_id_asks_for_update(api, student, admin_user):
    """Eski desktop (ID yubormaydi) bilan kirib bo'lmaydi — aks holda qoida chetlanardi."""
    code = make_code(student, admin_user)
    response = login(api, code, device_id=None)
    assert response.status_code == 400
    assert "yangi versiya" in response.json()["detail"]
    code.refresh_from_db()
    assert code.device_id == ""


def test_binding_closes_legacy_sessions_from_unknown_computers(api, student, admin_user):
    """Ko'p martalik davrida ochilgan (ID'siz) desktop/web sessiyalari yopiladi, mobil qoladi."""
    for jti, platform in (("old-desk", "desktop"), ("old-web", "web"), ("phone", "mobile")):
        Device.objects.create(user=student, platform=platform, refresh_jti=jti)
    code = make_code(student, admin_user)
    login(api, code)
    active = set(Device.objects.filter(user=student, is_active=True)
                 .values_list("refresh_jti", flat=True))
    assert "old-desk" not in active and "old-web" not in active
    assert "phone" in active


def test_second_code_on_second_computer_keeps_first_session(api, student, admin_user):
    first, second = make_code(student, admin_user), make_code(student, admin_user)
    login(api, first, PC1)
    assert login(api, second, PC2).status_code == 200
    assert Device.objects.filter(user=student, machine_id=PC1, is_active=True).exists()


def test_admin_unbinds_code_for_new_computer(api, student, admin_user, auth):
    code = make_code(student, admin_user)
    login(api, code, PC1)
    auth(api, admin_user)
    response = api.post(f"/api/v1/manage/access-codes/{code.id}/unbind/")
    assert response.status_code == 200
    assert response.json()["is_bound"] is False
    # eski kompyuter sessiyasi yopiladi, yangisi kira oladi
    assert not Device.objects.filter(machine_id=PC1, is_active=True).exists()
    api.credentials()
    assert login(api, code, PC2).status_code == 200


def test_device_id_is_not_exposed_to_admin_api(api, student, admin_user, auth):
    code = make_code(student, admin_user)
    login(api, code)
    auth(api, admin_user)
    body = api.get(f"/api/v1/manage/access-codes/{code.id}/").json()
    assert "device_id" not in body
    assert body["is_bound"] is True and body["bound_at"]


def test_django_admin_unbind_action(client, student, admin_user, django_user_model, api):
    code = make_code(student, admin_user)
    login(api, code)
    boss = django_user_model.objects.create_superuser(phone="+998900000778", password="x")
    client.force_login(boss)
    response = client.post("/admin/accounts/accesscode/",
                           {"action": "unbind", "_selected_action": [code.pk]})
    assert response.status_code == 302
    code.refresh_from_db()
    assert code.device_id == "" and code.bound_at is None
