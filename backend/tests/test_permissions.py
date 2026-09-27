import pytest
from rest_framework.test import APIRequestFactory

from common.permissions import IsAdminRole, IsStudent, IsTeacherOrAdmin

pytestmark = pytest.mark.django_db

rf = APIRequestFactory()


def _req(user):
    request = rf.get("/")
    request.user = user
    return request


def test_new_user_defaults_to_student_role(student):
    assert student.role == "student"


def test_is_teacher_false_for_student(student):
    assert not student.is_teacher


def test_is_teacher_true_for_teacher(teacher):
    assert teacher.is_teacher


def test_is_teacher_true_for_admin(admin_user):
    assert admin_user.is_teacher


def test_is_content_admin_true_for_superuser(django_user_model):
    user = django_user_model.objects.create_superuser("+998901119999", "x")
    assert user.is_content_admin


def test_is_content_admin_false_for_teacher(teacher):
    assert not teacher.is_content_admin


def test_is_student_permission_accepts_student(student):
    assert IsStudent().has_permission(_req(student), None)


def test_is_student_permission_rejects_teacher(teacher):
    assert not IsStudent().has_permission(_req(teacher), None)


def test_teacher_or_admin_permission_rejects_student(student):
    assert not IsTeacherOrAdmin().has_permission(_req(student), None)


def test_teacher_or_admin_permission_accepts_teacher(teacher):
    assert IsTeacherOrAdmin().has_permission(_req(teacher), None)


def test_admin_role_permission_rejects_student(student):
    assert not IsAdminRole().has_permission(_req(student), None)


def test_admin_role_permission_rejects_teacher(teacher):
    assert not IsAdminRole().has_permission(_req(teacher), None)


def test_admin_role_permission_accepts_admin(admin_user):
    assert IsAdminRole().has_permission(_req(admin_user), None)


def test_permissions_reject_anonymous():
    from django.contrib.auth.models import AnonymousUser

    request = _req(AnonymousUser())
    assert not IsStudent().has_permission(request, None)
    assert not IsTeacherOrAdmin().has_permission(request, None)
    assert not IsAdminRole().has_permission(request, None)


def test_me_endpoint_exposes_role_read_only(api, student, auth):
    auth(api, student)
    body = api.get("/api/v1/auth/me/").json()
    assert body["role"] == "student"
    # Rolni o'zi o'zgartira olmaydi.
    api.patch("/api/v1/auth/me/", {"role": "admin"}, format="json")
    student.refresh_from_db()
    assert student.role == "student"
