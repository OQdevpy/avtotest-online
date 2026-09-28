"""`import_payment_dump` — eski dumpdata JSON'idan to'lov va hisobotlar."""

import json
from decimal import Decimal

import pytest
from django.core.management import call_command

from apps.billing.models import PaymentReport, Student, StudentPayment

pytestmark = pytest.mark.django_db


def _student(pk, phone):
    return {"model": "home.student", "pk": pk, "fields": {
        "name": f"Talaba {pk}", "branch": None, "phone": phone,
        "password": "123456", "hujjat": "-", "is_active": True, "is_online": False}}


def _payment(pk, student, amount="1000000.00", tolagani="400000.00"):
    return {"model": "home.studentpayment", "pk": pk, "fields": {
        "student": student, "amount": amount, "tolagani": tolagani,
        "created_at": "2025-01-30T19:00:00Z"}}


def _report(pk, payment, paid="150000.00", date="2025-02-04", comment="kartaga"):
    return {"model": "home.paymentreport", "pk": pk, "fields": {
        "student_payment": payment, "paid_amount": paid, "date": date,
        "comment": comment, "created_at": "2025-02-04T05:57:45Z"}}


def _run(tmp_path, rows, *extra):
    path = tmp_path / "d.json"
    path.write_text(json.dumps(rows), encoding="utf-8")
    call_command("import_payment_dump", str(path), *extra)


def _with_students(rows):
    return [_student(1, "901230001"), _student(2, "901230002")] + rows


def test_imports_payment_for_student_user(tmp_path):
    _run(tmp_path, _with_students([_payment(10, 1)]))
    payment = StudentPayment.objects.get(user__phone="+998901230001")
    assert payment.amount == Decimal("1000000.00")
    assert payment.tolagani == Decimal("400000.00")
    assert payment.user == Student.objects.get(phone="+998901230001").user


def test_creates_missing_student_from_dump(tmp_path):
    """To'lov talabasi bazada bo'lmasa ham, dumpdagi talaba yozuvidan yaratiladi."""
    _run(tmp_path, _with_students([_payment(10, 2)]))
    assert Student.objects.filter(phone="+998901230002").exists()


def test_imports_reports_without_double_counting(tmp_path):
    _run(tmp_path, _with_students([_payment(10, 1), _report(20, 10), _report(21, 10, paid="50000.00")]))
    payment = StudentPayment.objects.get(user__phone="+998901230001")
    assert payment.reports.count() == 2
    assert payment.tolagani == Decimal("400000.00")  # qayta oshirilmagan


def test_rerun_is_idempotent(tmp_path):
    rows = _with_students([_payment(10, 1), _report(20, 10)])
    _run(tmp_path, rows)
    _run(tmp_path, rows)
    assert StudentPayment.objects.count() == 1
    assert PaymentReport.objects.count() == 1


def test_existing_payment_not_overwritten(tmp_path):
    _run(tmp_path, _with_students([_payment(10, 1)]))
    StudentPayment.objects.update(tolagani=Decimal("900000.00"))
    _run(tmp_path, _with_students([_payment(10, 1)]))
    assert StudentPayment.objects.get().tolagani == Decimal("900000.00")


def test_dry_run_writes_nothing(tmp_path):
    _run(tmp_path, _with_students([_payment(10, 1), _report(20, 10)]), "--dry-run")
    assert StudentPayment.objects.count() == 0
    assert PaymentReport.objects.count() == 0
