import pytest
from django.apps import apps as django_apps
from django.contrib import admin
from django.contrib.auth.models import Group
from django.core.management import call_command

pytestmark = pytest.mark.django_db

OUR_APPS = ("accounts", "content", "exams", "progress", "billing",
            "notifications", "telegramauth")

# Faqat inline orqali boshqariladigan bog'lovchi modellar — ularga alohida
# admin sahifasi kerak emas (tartib ota yozuv ichida tahrirlanadi).
INLINE_ONLY = {"TicketQuestion", "BlitsQuestion", "ExamSessionQuestion"}


def test_every_model_is_registered_in_admin():
    missing = [
        f"{model._meta.app_label}.{model.__name__}"
        for model in django_apps.get_models()
        if model._meta.app_label in OUR_APPS
        and model not in admin.site._registry
        and not model._meta.auto_created  # M2M through jadvallar
        and model.__name__ not in INLINE_ONLY
    ]
    assert missing == []


def test_setup_groups_creates_both_groups(db):
    call_command("setup_groups")
    assert Group.objects.filter(name="teacher").exists()
    assert Group.objects.filter(name="admin").exists()


def test_setup_groups_is_idempotent(db):
    call_command("setup_groups")
    call_command("setup_groups")
    assert Group.objects.filter(name="teacher").count() == 1


def test_teacher_group_has_no_content_write_permission(db):
    call_command("setup_groups")
    codenames = set(
        Group.objects.get(name="teacher").permissions.values_list("codename", flat=True)
    )
    forbidden = {"add_question", "change_question", "delete_question",
                 "add_lesson", "change_lesson", "delete_lesson"}
    assert not (codenames & forbidden)


def test_teacher_group_can_view_progress(db):
    call_command("setup_groups")
    codenames = set(
        Group.objects.get(name="teacher").permissions.values_list("codename", flat=True)
    )
    assert "view_lessonresult" in codenames
    assert "view_mistake" in codenames


def test_teacher_group_cannot_view_payments(db):
    call_command("setup_groups")
    codenames = set(
        Group.objects.get(name="teacher").permissions.values_list("codename", flat=True)
    )
    assert "view_studentpayment" not in codenames


def test_admin_group_can_write_content_and_billing(db):
    call_command("setup_groups")
    codenames = set(
        Group.objects.get(name="admin").permissions.values_list("codename", flat=True)
    )
    assert {"add_question", "change_question", "delete_question"} <= codenames
    assert {"add_studentpayment", "change_studentpayment"} <= codenames


def test_admin_group_cannot_delete_users(db):
    call_command("setup_groups")
    codenames = set(
        Group.objects.get(name="admin").permissions.values_list("codename", flat=True)
    )
    assert "delete_user" not in codenames
