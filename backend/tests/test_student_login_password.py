"""Talaba (Student) kirishi: PIN yoki foydalanuvchi paroli.

PIN faqat bir tomonga sinxronlanadi (Student → User). Shef Django admin'da
foydalanuvchi parolini o'zgartirsa yoki talaba Telegram orqali parolni tiklasa,
PIN eskicha qoladi — kirish yangi parol bilan ham ishlashi kerak.
"""

import pytest

from apps.billing.models import Student

pytestmark = pytest.mark.django_db

URL = "/api/v1/auth/login/"


def login(api, phone, password):
    return api.post(URL, {"phone": phone, "password": password}, format="json")


@pytest.fixture
def student_row(branch_a):
    return Student.objects.create(name="Ali", phone="901234590", password="777700", branch=branch_a)


def test_pin_still_works(api, student_row):
    assert login(api, "901234590", "777700").status_code == 200


def test_password_changed_in_admin_works(api, student_row):
    user = student_row.user
    user.set_password("YangiParol2026")   # Django admin'dagi "parolni o'zgartirish"
    user.save()
    response = login(api, "901234590", "YangiParol2026")
    assert response.status_code == 200, response.data
    assert response.data["user"]["phone"] == "+998901234590"


def test_wrong_password_rejected(api, student_row):
    response = login(api, "901234590", "notogri123")
    assert response.status_code == 400
    assert "noto'g'ri" in str(response.data)


def test_inactive_student_blocked_even_with_user_password(api, student_row):
    user = student_row.user
    user.set_password("YangiParol2026")
    user.save()
    Student.objects.filter(pk=student_row.pk).update(is_active=False)
    response = login(api, "901234590", "YangiParol2026")
    assert response.status_code == 400
    assert "bloklangan" in str(response.data)


def test_telegram_reset_password_lets_student_log_in(api, student_row, monkeypatch):
    from apps.telegramauth import otpstore

    monkeypatch.setattr(otpstore, "consume_token", lambda token, phone, purpose: True)
    response = api.post("/api/v1/auth/reset-password/", {
        "phone": "+998901234590", "token": "t", "password": "Tiklangan2026",
    }, format="json")
    assert response.status_code == 204, getattr(response, "data", None)
    assert login(api, "901234590", "Tiklangan2026").status_code == 200
