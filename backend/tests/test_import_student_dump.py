"""`import_student_dump` — eski tizim dumpdata JSON'idan filial+talaba import."""

import json

import pytest
from django.core.management import call_command

from apps.billing.models import Branch, Student

pytestmark = pytest.mark.django_db


def _fixture(path, rows):
    path.write_text(json.dumps(rows), encoding="utf-8")
    return str(path)


def _branch_row(pk, name):
    return {"model": "home.branch", "pk": pk, "fields": {"name": name}}


def _student_row(pk, name, branch, phone, password, hujjat="+", is_active=True):
    return {
        "model": "home.student", "pk": pk,
        "fields": {"name": name, "branch": branch, "phone": phone,
                   "password": password, "hujjat": hujjat, "is_active": is_active,
                   "is_online": False},
    }


def test_imports_branches_and_students(tmp_path):
    path = _fixture(tmp_path / "d.json", [
        _branch_row(1, "Xorazm"),
        _student_row(2, "Omonov Azizbek", 1, "901234500", "3005"),
    ])
    call_command("import_student_dump", path)

    branch = Branch.objects.get(name="Xorazm")
    student = Student.objects.get(phone="+998901234500")
    assert student.name == "Omonov Azizbek"
    assert student.branch_id == branch.id
    assert student.password == "3005"
    assert student.user.check_password("3005")
    assert student.user.role == "student"


def test_dedupes_branch_apostrophe_variants(tmp_path):
    path = _fixture(tmp_path / "d.json", [
        _branch_row(9, "Farg‘ona"),
        _branch_row(15, "Farg’ona"),
    ])
    call_command("import_student_dump", path)
    assert Branch.objects.count() == 1


def test_student_without_branch(tmp_path):
    path = _fixture(tmp_path / "d.json", [
        _student_row(5, "Kimdir", None, "901234501", "1102"),
    ])
    call_command("import_student_dump", path)
    student = Student.objects.get(phone="+998901234501")
    assert student.branch is None


def test_invalid_phone_is_skipped(tmp_path):
    path = _fixture(tmp_path / "d.json", [
        _student_row(6, "Yaroqsiz", None, "12", "1234"),
    ])
    call_command("import_student_dump", path)
    assert Student.objects.count() == 0


def test_existing_student_not_overwritten(tmp_path):
    Student.objects.create(name="Eski ism", phone="901234502", password="999999")
    path = _fixture(tmp_path / "d.json", [
        _student_row(7, "Yangi ism", None, "901234502", "1234"),
    ])
    call_command("import_student_dump", path)
    student = Student.objects.get(phone="+998901234502")
    assert student.name == "Eski ism"
    assert student.password == "999999"


def test_idempotent_rerun(tmp_path):
    path = _fixture(tmp_path / "d.json", [
        _student_row(8, "Ali", None, "901234503", "1234"),
    ])
    call_command("import_student_dump", path)
    call_command("import_student_dump", path)
    assert Student.objects.filter(phone="+998901234503").count() == 1


def test_dry_run_writes_nothing(tmp_path):
    path = _fixture(tmp_path / "d.json", [
        _student_row(9, "Ali", None, "901234504", "1234"),
    ])
    call_command("import_student_dump", path, "--dry-run")
    assert Student.objects.count() == 0
