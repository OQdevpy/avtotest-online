"""Yakuniy review topilmalari: mehmon refresh'i, bloklangan talaba, talabani tahrirlash, cheklov."""

from datetime import timedelta

from django.utils import timezone

from apps.accounts.models import Device, User
from apps.billing.models import Student
from tests.helpers import telegram_login

PHONE = "+998901234567"


def test_expired_guest_refresh_says_guest_expired(api, db):
    """Access token eskirgan mehmon refresh qilsa ham `guest_expired` — ilova tokenni saqlaydi."""
    r = api.post("/api/v1/auth/guest/", {"device_id": "a" * 32}, format="json")
    Device.objects.filter(user_id=r.data["user"]["id"]).update(
        expires_at=timezone.now() - timedelta(days=1), is_active=False)
    res = api.post("/api/v1/auth/token/refresh/", {"refresh": r.data["tokens"]["refresh"]},
                   format="json")
    assert res.status_code == 401
    assert res.data["code"] == "guest_expired"


def test_closed_student_refresh_not_guest_expired(api, student, fake_redis):
    login = telegram_login(api, student.phone)
    Device.objects.filter(user=student).update(is_active=False)
    res = api.post("/api/v1/auth/token/refresh/", {"refresh": login.data["tokens"]["refresh"]},
                   format="json")
    assert res.status_code == 401
    assert res.data.get("code") != "guest_expired"


def test_staff_edits_reset_student_without_pin(api, auth, admin_user, db):
    student = Student.objects.create(name="Talaba", phone=PHONE, password="1234")
    user = User.objects.get(phone=PHONE)
    user.set_password("ozimniki1")
    user.save()
    Student.objects.filter(pk=student.pk).update(password="")

    auth(api, admin_user)
    res = api.patch(f"/api/v1/manage/students/{student.pk}/", {"name": "Yangi ism", "password": ""},
                    format="json")
    assert res.status_code == 200, res.data
    user.refresh_from_db()
    assert user.full_name == "Yangi ism"
    assert user.check_password("ozimniki1")
    assert Student.objects.get(pk=student.pk).password == ""


def test_blank_pin_save_does_not_blank_user_password(db):
    student = Student.objects.create(name="Talaba", phone=PHONE, password="1234")
    student.password = ""
    student.save()
    user = User.objects.get(phone=PHONE)
    assert user.check_password("1234") and not user.check_password("")


def test_guest_rate_allows_carrier_nat(settings):
    """Bitta operator IP ortida soatiga 20 dan ko'p yangi o'rnatish bo'lishi mumkin."""
    from rest_framework.throttling import SimpleRateThrottle

    rate = SimpleRateThrottle.THROTTLE_RATES["guest"]
    num, period = rate.split("/")
    assert period.startswith("h") and int(num) >= 200
