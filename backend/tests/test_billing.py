from decimal import Decimal

import pytest

pytestmark = pytest.mark.django_db


# --- Modellar ---------------------------------------------------------------

def test_user_branch_is_nullable(student):
    assert student.branch is None


def test_user_hujjat_defaults_to_minus(student):
    assert student.hujjat == "-"


def test_qoldiq_is_amount_minus_paid(payment):
    assert payment.qoldiq == Decimal("1000000")


def test_payment_report_updates_tolagani(api, admin_user, auth, payment):
    auth(api, admin_user)
    response = api.post("/api/v1/manage/payment-reports/",
                        {"student_payment": payment.id, "paid_amount": "250000"},
                        format="json")
    assert response.status_code == 201
    payment.refresh_from_db()
    assert payment.tolagani == Decimal("250000")


def test_two_reports_accumulate(api, admin_user, auth, payment):
    auth(api, admin_user)
    for _ in range(2):
        api.post("/api/v1/manage/payment-reports/",
                 {"student_payment": payment.id, "paid_amount": "100000"},
                 format="json")
    payment.refresh_from_db()
    assert payment.tolagani == Decimal("200000")
    assert payment.qoldiq == Decimal("800000")


# --- Ruxsat -----------------------------------------------------------------

def test_student_cannot_list_payments(api, student, auth):
    auth(api, student)
    assert api.get("/api/v1/manage/payments/").status_code == 403


def test_teacher_cannot_list_payments(api, teacher, auth):
    auth(api, teacher)
    assert api.get("/api/v1/manage/payments/").status_code == 403


def test_admin_can_list_payments(api, admin_user, auth, payment):
    auth(api, admin_user)
    assert api.get("/api/v1/manage/payments/").status_code == 200


def test_admin_creates_branch(api, admin_user, auth):
    auth(api, admin_user)
    assert api.post("/api/v1/manage/branches/",
                    {"name": "Sergeli filiali"}, format="json").status_code == 201


def test_student_cannot_create_branch(api, student, auth):
    auth(api, student)
    assert api.post("/api/v1/manage/branches/",
                    {"name": "X"}, format="json").status_code == 403


# --- manage/users/ ----------------------------------------------------------

def test_admin_creates_student_with_hashed_password(api, admin_user, auth, branch_a):
    from apps.accounts.models import User

    auth(api, admin_user)
    response = api.post("/api/v1/manage/users/",
                        {"phone": "901234567", "full_name": "Ali",
                         "password": "1234", "branch": branch_a.id}, format="json")
    assert response.status_code == 201
    assert response.json()["phone"] == "+998901234567"
    assert "password" not in response.json()
    user = User.objects.get(phone="+998901234567")
    assert user.check_password("1234")
    assert user.role == "student"


def test_admin_can_set_role(api, admin_user, auth):
    from apps.accounts.models import User

    auth(api, admin_user)
    api.post("/api/v1/manage/users/",
             {"phone": "901234568", "password": "1234", "role": "teacher"},
             format="json")
    assert User.objects.get(phone="+998901234568").role == "teacher"


def test_manage_users_filters_by_role(api, admin_user, auth, student, teacher):
    auth(api, admin_user)
    rows = api.get("/api/v1/manage/users/?role=teacher").json()["results"]
    assert [r["phone"] for r in rows] == [teacher.phone]


def test_manage_users_filters_by_branch(api, admin_user, auth, student, other_student,
                                        branch_a):
    student.branch = branch_a
    student.save(update_fields=["branch"])
    auth(api, admin_user)
    rows = api.get(f"/api/v1/manage/users/?branch={branch_a.id}").json()["results"]
    assert [r["phone"] for r in rows] == [student.phone]


def test_manage_users_search_matches_name_and_phone(api, admin_user, auth, student):
    auth(api, admin_user)
    assert len(api.get("/api/v1/manage/users/?search=O'quvchi").json()["results"]) == 1
    assert len(api.get("/api/v1/manage/users/?search=1110001").json()["results"]) == 1


def test_teacher_cannot_create_user(api, teacher, auth):
    auth(api, teacher)
    assert api.post("/api/v1/manage/users/",
                    {"phone": "901234569", "password": "1234"},
                    format="json").status_code == 403


def test_admin_updates_user_password(api, admin_user, auth, student):
    auth(api, admin_user)
    response = api.patch(f"/api/v1/manage/users/{student.id}/",
                         {"password": "yangi1234"}, format="json")
    assert response.status_code == 200
    student.refresh_from_db()
    assert student.check_password("yangi1234")


def test_invalid_phone_rejected(api, admin_user, auth):
    auth(api, admin_user)
    assert api.post("/api/v1/manage/users/",
                    {"phone": "123", "password": "1234"},
                    format="json").status_code == 400
