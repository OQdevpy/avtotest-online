"""`auth/telegram/claim/` — tasdiqlangan Telegram kontakti bo'yicha kirish yoki hisob ochish."""

from datetime import timedelta

from django.utils import timezone

from apps.accounts.models import Device, User
from apps.billing.models import Student
from apps.progress.models import SavedQuestion
from apps.telegramauth import verification
from apps.telegramauth.models import TelegramAccount

CLAIM = "/api/v1/auth/telegram/claim/"
PHONE = "+998901234567"


def verified_token(phone=PHONE, name="Ali Valiyev", telegram_id=7):
    token = verification.start_session(None, "auth", "uz", ip="10.0.0.1")
    verification.resolve_contact(token, phone, telegram_id, name)
    return token


def claim(api, token, **extra):
    return api.post(CLAIM, {"token": token, **extra}, format="json")


def make_guest(api):
    return api.post("/api/v1/auth/guest/", {"device_id": "a" * 32}, format="json").data


def test_claim_creates_student(api, db, fake_redis):
    r = claim(api, verified_token())
    assert r.status_code == 201, r.data
    assert r.data["created"] is True
    assert set(r.data["tokens"]) == {"access", "refresh"}
    user = User.objects.get(phone=PHONE)
    assert user.role == "student"
    assert user.full_name == "Ali Valiyev"
    assert user.pro_active
    assert user.has_usable_password() is False


def test_claim_existing_user_logs_in(api, student, fake_redis):
    before = User.objects.count()
    r = claim(api, verified_token(student.phone))
    assert r.status_code == 200, r.data
    assert r.data["created"] is False
    assert r.data["user"]["id"] == student.pk
    assert User.objects.count() == before
    student.refresh_from_db()
    assert student.full_name == "O'quvchi"


def test_claim_converts_guest_keeps_progress(api, db, fake_redis, question):
    guest = make_guest(api)
    guest_user = User.objects.get(pk=guest["user"]["id"])
    SavedQuestion.objects.create(user=guest_user, question=question)

    r = claim(api, verified_token(), guest_refresh=guest["tokens"]["refresh"])

    assert r.status_code == 201, r.data
    assert r.data["user"]["id"] == guest_user.pk
    guest_user.refresh_from_db()
    assert guest_user.role == "student" and guest_user.phone == PHONE
    assert guest_user.full_name == "Ali Valiyev"
    assert guest_user.pro_active
    assert SavedQuestion.objects.filter(user=guest_user).exists()


def test_claim_converts_expired_guest(api, db, fake_redis):
    guest = make_guest(api)
    Device.objects.filter(user_id=guest["user"]["id"]).update(
        expires_at=timezone.now() - timedelta(days=3), is_active=False)

    r = claim(api, verified_token(), guest_refresh=guest["tokens"]["refresh"])

    assert r.status_code == 201, r.data
    assert r.data["user"]["id"] == guest["user"]["id"]


def test_claim_existing_with_guest_refresh(api, student, fake_redis):
    guest = make_guest(api)
    guest_id = guest["user"]["id"]

    r = claim(api, verified_token(student.phone), guest_refresh=guest["tokens"]["refresh"])

    assert r.status_code == 200, r.data
    assert r.data["user"]["id"] == student.pk
    assert User.objects.get(pk=guest_id).role == "guest"
    assert not Device.objects.filter(user_id=guest_id, is_active=True).exists()


def test_claim_blocked_user(api, student, fake_redis):
    User.objects.filter(pk=student.pk).update(is_active=False)
    r = claim(api, verified_token(student.phone))
    assert r.status_code == 403
    assert r.data["code"] == "blocked"
    assert "tokens" not in r.data


def test_claim_blocked_student(api, db, fake_redis):
    Student.objects.create(name="Talaba", phone=PHONE, password="1234", is_active=False)
    r = claim(api, verified_token())
    assert r.status_code == 403
    assert r.data["code"] == "blocked"
    assert "tokens" not in r.data


def test_claim_single_use(api, db, fake_redis):
    token = verified_token()
    assert claim(api, token).status_code == 201
    r = claim(api, token)
    assert r.status_code == 400
    assert r.data["code"] == "verification_invalid"


def test_claim_not_verified(api, db, fake_redis):
    pending = verification.start_session(None, "auth", "uz", ip="10.0.0.1")
    assert claim(api, pending).status_code == 400

    foreign = verified_token(phone="+79001234567")
    r = claim(api, foreign)
    assert r.status_code == 400
    assert r.data["code"] == "verification_invalid"


def test_claim_links_telegram_account(api, db, fake_redis):
    TelegramAccount.objects.create(telegram_id=7, phone=PHONE)
    r = claim(api, verified_token(telegram_id=7))
    assert r.status_code == 201
    assert TelegramAccount.objects.get(telegram_id=7).user_id == r.data["user"]["id"]


def test_claim_platform_web_session(api, db, fake_redis):
    r = claim(api, verified_token(), platform="web", device_label="Admin Panel")
    assert r.status_code == 201
    device = Device.objects.get(user_id=r.data["user"]["id"])
    assert device.platform == "web"
    assert device.label == "Admin Panel"


# --- Eski avtotest bazasidan ko'chirish (apps/telegramauth/legacy.py) -------

def legacy_row(**over):
    data = {"full_name": "Eski Foydalanuvchi", "language": "ru", "is_pro": False,
            "pro_until": None, "is_active": True,
            "date_joined": timezone.now() - timedelta(days=300)}
    data.update(over)
    return data


def test_legacy_user_reads_student_by_phone(db, settings):
    from apps.telegramauth import legacy

    settings.LEGACY_DB_ALIAS = "default"  # testda "eski baza" — shu baza
    until = timezone.now() + timedelta(days=30)
    User.objects.create(phone=PHONE, full_name="Eski", language="qq", is_pro=True,
                        pro_until=until)
    User.objects.create(phone="+998907777777", role="teacher")

    data = legacy.legacy_user(PHONE)
    assert data["full_name"] == "Eski" and data["language"] == "uz"
    assert data["is_pro"] is True and abs((data["pro_until"] - until).total_seconds()) < 1
    assert legacy.pro_active(data)
    assert legacy.legacy_user("+998907777777") is None  # faqat o'quvchilar
    assert legacy.legacy_user("+998900000001") is None


def test_legacy_disabled_without_alias(db):
    from apps.telegramauth import legacy

    assert legacy.legacy_user(PHONE) is None


def test_claim_imports_legacy_account(api, db, fake_redis, monkeypatch):
    from apps.telegramauth import legacy

    until = timezone.now() + timedelta(days=100)
    joined = timezone.now() - timedelta(days=300)
    monkeypatch.setattr(legacy, "legacy_user", lambda phone: legacy_row(
        is_pro=True, pro_until=until, date_joined=joined) if phone == PHONE else None)

    r = claim(api, verified_token(name="Telegram Ism"))
    assert r.status_code == 201, r.data
    user = User.objects.get(phone=PHONE)
    assert user.full_name == "Eski Foydalanuvchi"
    assert user.language == "ru"
    assert user.pro_until == until  # eski PRO sovg'adan uzunroq — saqlanadi
    assert user.date_joined == joined


def test_claim_legacy_expired_pro_gets_welcome(api, db, fake_redis, monkeypatch):
    from apps.telegramauth import legacy

    monkeypatch.setattr(legacy, "legacy_user", lambda phone: legacy_row(
        is_pro=True, pro_until=timezone.now() - timedelta(days=1)))
    assert claim(api, verified_token()).status_code == 201
    user = User.objects.get(phone=PHONE)
    assert user.pro_active and user.pro_until > timezone.now() + timedelta(days=11)


def test_claim_legacy_lifetime_pro(api, db, fake_redis, monkeypatch):
    from apps.telegramauth import legacy

    monkeypatch.setattr(legacy, "legacy_user", lambda phone: legacy_row(is_pro=True))
    assert claim(api, verified_token()).status_code == 201
    assert User.objects.get(phone=PHONE).pro_until is None


def test_claim_legacy_blocked_stays_blocked(api, db, fake_redis, monkeypatch):
    from apps.telegramauth import legacy

    monkeypatch.setattr(legacy, "legacy_user", lambda phone: legacy_row(is_active=False))
    assert claim(api, verified_token()).status_code == 403


def test_claim_existing_user_ignores_legacy(api, student, fake_redis, monkeypatch):
    from apps.telegramauth import legacy

    monkeypatch.setattr(legacy, "legacy_user", lambda phone: legacy_row())
    r = claim(api, verified_token(student.phone))
    assert r.status_code == 200
    student.refresh_from_db()
    assert student.full_name == "O'quvchi"


def test_legacy_db_error_returns_none(settings, monkeypatch):
    from django.db import DatabaseError
    from apps.telegramauth import legacy

    class Broken:
        def cursor(self):
            raise DatabaseError("ulanib bo'lmadi")

    settings.LEGACY_DB_ALIAS = "default"
    monkeypatch.setattr(legacy, "connections", {"default": Broken()})
    assert legacy.legacy_user(PHONE) is None  # kirish to'xtamaydi
