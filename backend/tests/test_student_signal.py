"""Student modeli va uni User bilan bog'laydigan signal.

Talaba yozuvi eski web/backend'dagi `home.Student` shaklida: parol ochiq
matnda (front-ofis xodimi o'quvchiga aytib berishi uchun). Mobil ilovaning
kirishi shu Student.password bilan tekshiriladi, lekin JWT token har doim
bog'liq `accounts.User` uchun chiqariladi — Student saqlanganda signal shu
User'ni avtomatik yaratadi/yangilaydi (parolni hash qilib).
"""

import pytest

from apps.billing.models import Student

pytestmark = pytest.mark.django_db


def test_creating_student_creates_linked_user(branch_a):
    student = Student.objects.create(
        name="Ali Valiyev", phone="901234567", password="123456",
        branch=branch_a, hujjat="+",
    )
    student.refresh_from_db()
    assert student.user is not None
    assert student.user.phone == "+998901234567"
    assert student.user.role == "student"
    assert student.user.full_name == "Ali Valiyev"
    assert student.user.branch_id == branch_a.id
    assert student.user.hujjat == "+"


def test_created_user_password_matches_plaintext_pin(branch_a):
    student = Student.objects.create(name="Ali", phone="901234568", password="456800")
    student.refresh_from_db()
    assert student.user.check_password("456800")


def test_student_password_stays_plaintext_on_the_student_row():
    """Student.password — ochiq matn, User.password — hash. Ikkisi bir maydon emas."""
    student = Student.objects.create(name="Ali", phone="901234569", password="456900")
    assert student.password == "456900"
    student.refresh_from_db()
    assert student.user.password != "456900"


def test_existing_user_is_linked_but_password_not_overwritten(django_user_model):
    """Mobil ilovada o'z parolini o'rnatgan foydalanuvchi PIN bilan almashtirilmaydi."""
    existing = django_user_model.objects.create_user(
        "+998901234570", "haqiqiy-parol-123", full_name="Eski ism",
    )
    student = Student.objects.create(name="Yangi ism", phone="901234570", password="457000")
    student.refresh_from_db()
    assert student.user_id == existing.id
    existing.refresh_from_db()
    assert existing.check_password("haqiqiy-parol-123")
    assert not existing.check_password("457000")
    assert existing.full_name == "Eski ism"


def test_editing_student_pin_updates_linked_user_password():
    student = Student.objects.create(name="Ali", phone="901234571", password="111100")
    student.password = "222200"
    student.save()
    student.refresh_from_db()
    assert student.user.check_password("222200")
    assert not student.user.check_password("111100")


def test_editing_student_branch_syncs_to_user(branch_a, branch_b):
    student = Student.objects.create(name="Ali", phone="901234572", password="111100",
                                     branch=branch_a)
    student.branch = branch_b
    student.save()
    student.refresh_from_db()
    assert student.user.branch_id == branch_b.id


def test_student_phone_is_normalized_on_save(branch_a):
    student = Student.objects.create(name="Ali", phone="+998 90 123 45 73", password="111100")
    student.refresh_from_db()
    assert student.phone == "+998901234573"
    assert student.user.phone == "+998901234573"


def test_invalid_student_phone_rejected():
    from django.core.exceptions import ValidationError

    with pytest.raises(ValidationError):
        Student.objects.create(name="Ali", phone="123", password="111100")


def test_django_admin_shows_plaintext_password():
    from django.contrib import admin

    model_admin = admin.site._registry[Student]
    assert "password" in model_admin.list_display


def test_admin_creates_student_via_manage_endpoint(api, admin_user, auth, branch_a):
    auth(api, admin_user)
    response = api.post("/api/v1/manage/students/", {
        "name": "Vali", "phone": "901234574", "password": "123400", "branch": branch_a.id,
    }, format="json")
    assert response.status_code == 201, response.data
    student = Student.objects.get(phone="+998901234574")
    assert student.user.check_password("123400")


def test_manage_endpoint_rejects_short_password(api, admin_user, auth):
    auth(api, admin_user)
    response = api.post("/api/v1/manage/students/", {
        "name": "X", "phone": "901234576", "password": "1234",
    }, format="json")
    assert response.status_code == 400
    assert "password" in response.data


def test_student_cannot_create_student(api, student, auth):
    auth(api, student)
    assert api.post("/api/v1/manage/students/", {
        "name": "X", "phone": "901234575", "password": "123400",
    }, format="json").status_code == 403


def test_mobile_login_uses_student_password(api, branch_a):
    """Mobil kirish Student.password (ochiq PIN) bilan tekshiriladi."""
    Student.objects.create(name="Ali", phone="901234580", password="777700", branch=branch_a)
    response = api.post("/api/v1/auth/login/", {
        "phone": "901234580", "password": "777700", "platform": "web",
    }, format="json")
    assert response.status_code == 200, response.data
    assert response.data["user"]["phone"] == "+998901234580"
