"""Eski web bazasidan foydalanuvchi va to'lov importi.

Sinovda eski baza sqlite'da yasaladi — sxema haqiqiy `home` app'idagi jadval
nomlari bilan bir xil.
"""

import sqlite3
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.accounts.models import User
from apps.billing.models import Branch, PaymentReport, StudentPayment

pytestmark = pytest.mark.django_db


def build_old_db(path, *, students=None, bad_phone=False):
    connection = sqlite3.connect(path)
    cursor = connection.cursor()
    cursor.executescript(
        """
        CREATE TABLE home_branch (
            id INTEGER PRIMARY KEY, name TEXT,
            created_at TEXT, updated_at TEXT
        );
        CREATE TABLE home_student (
            id INTEGER PRIMARY KEY, name TEXT, branch_id INTEGER, phone TEXT,
            password TEXT, hujjat TEXT, created_at TEXT, updated_at TEXT,
            is_active INTEGER, is_online INTEGER
        );
        CREATE TABLE home_studentpayment (
            id INTEGER PRIMARY KEY, student_id INTEGER, amount TEXT,
            tolagani TEXT, created_at TEXT
        );
        CREATE TABLE home_paymentreport (
            id INTEGER PRIMARY KEY, student_payment_id INTEGER, paid_amount TEXT,
            date TEXT, comment TEXT, created_at TEXT
        );
        INSERT INTO home_branch VALUES (1, 'Chilonzor', '2024-01-01', '2024-01-01');
        """
    )
    rows = students or [(1, 'Ali Valiyev', 1, '901234567', '1234', '+', 1)]
    if bad_phone:
        rows = rows + [(99, 'Xato raqam', 1, '123', 'x', '-', 1)]
    for sid, name, branch, phone, password, hujjat, active in rows:
        cursor.execute(
            "INSERT INTO home_student VALUES (?,?,?,?,?,?,?,?,?,?)",
            (sid, name, branch, phone, password, hujjat,
             '2024-01-01', '2024-01-01', active, 0),
        )
    cursor.execute(
        "INSERT INTO home_studentpayment VALUES (1, 1, '1000000', '250000', '2024-01-01')"
    )
    cursor.execute(
        "INSERT INTO home_paymentreport VALUES "
        "(1, 1, '250000', '2024-02-01', 'birinchi to''lov', '2024-02-01')"
    )
    connection.commit()
    connection.close()
    return f"sqlite:///{path}"  # mutlaq yo'l: 3 slash + /tmp/...


@pytest.fixture
def old_db(tmp_path):
    return build_old_db(tmp_path / "web.sqlite3")


def run(url, **kwargs):
    call_command("import_web", database_url=url, **kwargs)


# --- Asosiy oqim ------------------------------------------------------------

def test_branch_is_imported(db, old_db):
    run(old_db)
    assert Branch.objects.filter(name="Chilonzor").exists()


def test_student_becomes_user_with_normalized_phone(db, old_db):
    run(old_db)
    user = User.objects.get(phone="+998901234567")
    assert user.full_name == "Ali Valiyev"
    assert user.role == "student"
    assert user.hujjat == "+"
    assert user.branch.name == "Chilonzor"


def test_plaintext_password_is_hashed(db, old_db):
    run(old_db)
    user = User.objects.get(phone="+998901234567")
    assert user.password != "1234"
    assert user.check_password("1234")


def test_payment_and_report_are_imported(db, old_db):
    run(old_db)
    user = User.objects.get(phone="+998901234567")
    payment = StudentPayment.objects.get(user=user)
    assert payment.amount == Decimal("1000000")
    assert payment.tolagani == Decimal("250000")
    assert PaymentReport.objects.filter(student_payment=payment).count() == 1


def test_report_import_does_not_double_count(db, old_db):
    """Hisobot importi `tolagani` ni qayta oshirmasligi kerak."""
    run(old_db)
    payment = StudentPayment.objects.get()
    assert payment.tolagani == Decimal("250000")


# --- Review Focus #5: telefon to'qnashuvi ------------------------------------

def test_existing_user_is_not_overwritten(db, old_db):
    existing = User.objects.create_user("+998901234567", "eski-parol",
                                        full_name="Mavjud Foydalanuvchi")
    old_hash = existing.password
    run(old_db)
    existing.refresh_from_db()
    assert existing.password == old_hash
    assert existing.full_name == "Mavjud Foydalanuvchi"
    assert existing.check_password("eski-parol")
    assert not existing.check_password("1234")


def test_existing_user_gets_empty_fields_filled(db, old_db):
    existing = User.objects.create_user("+998901234567", "eski-parol")
    run(old_db)
    existing.refresh_from_db()
    assert existing.branch is not None
    assert existing.hujjat == "+"


def test_existing_user_keeps_progress(db, old_db, lesson):
    from apps.progress.models import LessonResult

    existing = User.objects.create_user("+998901234567", "eski-parol")
    LessonResult.objects.create(user=existing, lesson=lesson, score=4, total=5)
    run(old_db)
    assert LessonResult.objects.filter(user=existing).count() == 1


def test_no_duplicate_user_created(db, old_db):
    User.objects.create_user("+998901234567", "eski-parol")
    run(old_db)
    assert User.objects.filter(phone="+998901234567").count() == 1


# --- Chidamlilik ------------------------------------------------------------

def test_invalid_phone_is_reported_not_raised(db, tmp_path):
    url = build_old_db(tmp_path / "web2.sqlite3", bad_phone=True)
    run(url)
    # To'g'ri raqam ko'chdi, xatosi o'tkazib yuborildi.
    assert User.objects.filter(phone="+998901234567").exists()
    assert User.objects.count() == 1


def test_is_idempotent(db, old_db):
    run(old_db)
    run(old_db)
    assert User.objects.filter(phone="+998901234567").count() == 1
    assert StudentPayment.objects.count() == 1
    assert PaymentReport.objects.count() == 1
    assert StudentPayment.objects.get().tolagani == Decimal("250000")


def test_dry_run_writes_nothing(db, old_db):
    run(old_db, dry_run=True)
    assert User.objects.count() == 0
    assert Branch.objects.count() == 0


def test_unknown_scheme_raises(db):
    with pytest.raises(CommandError):
        run("mysql://user@host/db")


def test_missing_sqlite_file_raises(db, tmp_path):
    with pytest.raises(CommandError):
        run(f"sqlite:///{tmp_path / 'yoq.sqlite3'}")
