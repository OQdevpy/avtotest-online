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


# --- Important #6: nashr etilmagan savol saqlanganlar va xatolar orqali ------

def test_cannot_save_unpublished_question(api, student, auth, lesson, make_question):
    draft = make_question(lesson, "Qoralama", order=9, published=False)
    auth(api, student)
    response = api.post("/api/v1/progress/saved/", {"question": draft.id}, format="json")
    assert response.status_code == 400


def test_saved_list_excludes_unpublished(api, student, auth, lesson, make_question):
    from apps.progress.models import SavedQuestion

    draft = make_question(lesson, "Qoralama", order=9, published=False)
    SavedQuestion.objects.create(user=student, question=draft)
    auth(api, student)
    body = api.get("/api/v1/progress/saved/").json()
    rows = body["results"] if isinstance(body, dict) else body
    assert rows == []


def test_cannot_submit_result_for_unpublished_question(api, student, auth, lesson,
                                                      make_question):
    draft = make_question(lesson, "Qoralama", order=9, published=False)
    auth(api, student)
    response = api.post("/api/v1/progress/lesson-results/", {
        "lesson": lesson.id,
        "items": [{"question": draft.id, "answer": None}],
    }, format="json")
    assert response.status_code == 400


def test_mistakes_list_excludes_unpublished(api, student, auth, lesson, make_question):
    from apps.progress.models import Mistake

    draft = make_question(lesson, "Qoralama", order=9, published=False)
    Mistake.objects.create(user=student, question=draft, wrong_count=3)
    auth(api, student)
    body = api.get("/api/v1/progress/mistakes/").json()
    rows = body["results"] if isinstance(body, dict) else body
    assert rows == []


# --- Important #7: platform mijoz tomonidan aytilmasligi --------------------

def test_login_code_cannot_claim_mobile_platform(api, student, admin_user):
    from apps.accounts.models import AccessCode

    code = AccessCode.generate(user=student, created_by=admin_user)
    api.post("/api/v1/auth/login-code/",
             {"code": code.code, "platform": "mobile"}, format="json")
    device = Device.objects.get(user=student)
    assert device.platform == "desktop"


# --- Important #8: question_count nashr holatini hisobga olishi -------------

def test_ticket_question_count_excludes_unpublished(api, student, auth, ticket, lesson,
                                                   make_question):
    from apps.content.models import TicketQuestion

    draft = make_question(lesson, "Qoralama", order=9, published=False)
    TicketQuestion.objects.create(ticket=ticket, question=draft, order=1)
    auth(api, student)
    body = api.get("/api/v1/tickets/").json()["results"][0]
    assert body["question_count"] == 1


def test_lesson_question_count_excludes_unpublished(api, student, auth, lesson,
                                                   make_question, question):
    make_question(lesson, "Qoralama", order=9, published=False)
    auth(api, student)
    # lessons/ sahifalanmaydi — to'g'ridan-to'g'ri ro'yxat.
    rows = api.get(f"/api/v1/lessons/?section={lesson.section_id}").json()
    assert rows[0]["question_count"] == 1


def test_topic_question_count_excludes_unpublished(api, student, auth, lesson,
                                                   make_question, question):
    """`Mavzular` = `Darslar` — hisob ham dars bo'yicha keladi."""
    make_question(lesson, "Qoralama", order=9, published=False)
    auth(api, student)
    assert api.get("/api/v1/topics/").json()[0]["question_count"] == 1


# --- Important #10: qurilma limiti poyga holatida ham ishlashi --------------

def test_register_device_locks_the_user_row(student):
    """Limit tekshiruvi foydalanuvchi qatorini qulflashi kerak."""
    import inspect

    from apps.accounts import devices

    source = inspect.getsource(devices.register_device)
    assert "select_for_update" in source


# --- Minor: noto'g'ri filtr qiymati 500 emas, 400 bermasligi ----------------

def test_invalid_lesson_filter_returns_400(api, student, auth, question):
    auth(api, student)
    assert api.get("/api/v1/questions/?lesson=abc").status_code == 400


def test_invalid_branch_filter_returns_400(api, admin_user, auth):
    # `?branch=` faqat shefda o'qiladi — o'qituvchi baribir o'z filialini ko'radi.
    auth(api, admin_user)
    assert api.get("/api/v1/teacher/students/?branch=abc").status_code == 400


# --- Minor: kod muddati 403 dan keyin boshlanmasligi ------------------------

# --- Important #5: hisobot tahrirlansa/o'chirilsa balans to'g'ri qolishi -----

def test_editing_report_adjusts_balance(api, admin_user, auth, payment):
    from decimal import Decimal

    auth(api, admin_user)
    created = api.post("/api/v1/manage/payment-reports/",
                       {"student_payment": payment.id, "paid_amount": "500000"},
                       format="json").json()
    api.patch(f"/api/v1/manage/payment-reports/{created['id']}/",
              {"paid_amount": "50000"}, format="json")
    payment.refresh_from_db()
    assert payment.tolagani == Decimal("50000")


def test_deleting_report_reduces_balance(api, admin_user, auth, payment):
    from decimal import Decimal

    auth(api, admin_user)
    created = api.post("/api/v1/manage/payment-reports/",
                       {"student_payment": payment.id, "paid_amount": "500000"},
                       format="json").json()
    api.delete(f"/api/v1/manage/payment-reports/{created['id']}/")
    payment.refresh_from_db()
    assert payment.tolagani == Decimal("0")


# --- Important #4: import_web qayta ishlatilsa balansni buzmasligi ----------

def test_import_web_rerun_keeps_later_payments(db, tmp_path):
    from decimal import Decimal

    from django.core.management import call_command

    from apps.billing.models import StudentPayment
    from tests.test_import_web import build_old_db

    url = build_old_db(tmp_path / "w.sqlite3")
    call_command("import_web", database_url=url)
    payment = StudentPayment.objects.get()
    # Shef importdan keyin yangi to'lov qabul qildi.
    from apps.billing.models import PaymentReport

    PaymentReport.objects.create(student_payment=payment, paid_amount=Decimal("300000"))
    payment.refresh_from_db()
    assert payment.tolagani == Decimal("550000")

    call_command("import_web", database_url=url)
    payment.refresh_from_db()
    assert payment.tolagani == Decimal("550000")


def test_import_web_colliding_phones_do_not_overwrite_payment(db, tmp_path):
    from decimal import Decimal

    from django.core.management import call_command

    from apps.billing.models import StudentPayment
    from tests.test_import_web import build_old_db

    # Ikki eski yozuv bitta +998 raqamiga normallashadi.
    url = build_old_db(tmp_path / "w2.sqlite3", students=[
        (1, "Birinchi", 1, "901234567", "1234", "+", 1),
        (2, "Ikkinchi", 1, "90 123 45 67", "5678", "-", 1),
    ])
    call_command("import_web", database_url=url)
    assert StudentPayment.objects.count() == 1
    assert StudentPayment.objects.get().amount == Decimal("1000000")


def test_import_web_keeps_repeated_same_day_reports(db, tmp_path):
    import sqlite3

    from django.core.management import call_command

    from apps.billing.models import PaymentReport
    from tests.test_import_web import build_old_db

    path = tmp_path / "w3.sqlite3"
    url = build_old_db(path)
    connection = sqlite3.connect(path)
    connection.execute(
        "INSERT INTO home_paymentreport VALUES "
        "(2, 1, '250000', '2024-02-01', 'ikkinchi', '2024-02-01')"
    )
    connection.commit()
    connection.close()
    call_command("import_web", database_url=url)
    assert PaymentReport.objects.count() == 2


# --- Important #9: Django adminda yangi maydonlar boshqarilishi -------------

def _admin_fields(model_admin):
    """`fieldsets` dagi barcha maydon nomlari."""
    names = set()
    for _, options in model_admin.fieldsets or ():
        for field in options.get("fields", ()):
            if isinstance(field, (tuple, list)):
                names.update(field)
            else:
                names.add(field)
    return names


def test_user_admin_exposes_role_branch_hujjat_and_limit():
    from django.contrib import admin as dj_admin

    from apps.accounts.models import User

    fields = _admin_fields(dj_admin.site._registry[User])
    assert {"role", "branch", "hujjat", "max_devices"} <= fields


def test_user_admin_can_filter_by_role_and_branch():
    from django.contrib import admin as dj_admin

    from apps.accounts.models import User

    model_admin = dj_admin.site._registry[User]
    assert "role" in model_admin.list_filter
    assert "branch" in model_admin.list_filter
    assert "role" in model_admin.list_display


def test_question_admin_shows_publish_state():
    from django.contrib import admin as dj_admin

    from apps.content.models import Question

    model_admin = dj_admin.site._registry[Question]
    assert "is_published" in model_admin.list_display
    assert "is_published" in model_admin.list_filter


def test_question_admin_can_bulk_publish():
    from django.contrib import admin as dj_admin

    from apps.content.models import Question

    model_admin = dj_admin.site._registry[Question]
    names = {getattr(a, "__name__", a) for a in model_admin.actions or ()}
    assert "publish" in names
    assert "unpublish" in names
