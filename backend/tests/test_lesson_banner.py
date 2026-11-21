"""Dars banneri — o'qituvchi ilovasida dars ochilganda savollardan oldin katta rasm."""

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.content.models import Lesson
from apps.content.version import content_version

pytestmark = pytest.mark.django_db


@pytest.fixture
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    (tmp_path / "images").mkdir()
    return tmp_path


def png(color="red"):
    buffer = io.BytesIO()
    Image.new("RGB", (40, 20), color).save(buffer, "PNG")
    return SimpleUploadedFile("banner.png", buffer.getvalue(), "image/png")


def url(lesson):
    return f"/api/v1/manage/lessons/{lesson.id}/banner/"


def test_upload_banner_as_webp(api, admin_user, auth, lesson, media_root):
    auth(api, admin_user)
    r = api.post(url(lesson), {"file": png()})
    assert r.status_code == 200
    lesson.refresh_from_db()
    assert lesson.banner == r.data["banner"]
    assert lesson.banner.startswith(f"images/lesson{lesson.id}_banner_") and lesson.banner.endswith(".webp")
    assert (media_root / lesson.banner).exists()


def test_replace_removes_old_file_and_delete_clears(api, admin_user, auth, lesson, media_root):
    auth(api, admin_user)
    first = api.post(url(lesson), {"file": png("red")}).data["banner"]
    second = api.post(url(lesson), {"file": png("blue")}).data["banner"]
    assert first != second
    assert not (media_root / first).exists() and (media_root / second).exists()

    assert api.delete(url(lesson)).data == {"banner": ""}
    lesson.refresh_from_db()
    assert lesson.banner == "" and not (media_root / second).exists()


def test_bad_file_and_missing_file(api, admin_user, auth, lesson, media_root):
    auth(api, admin_user)
    bad = SimpleUploadedFile("x.png", b"not an image", "image/png")
    assert api.post(url(lesson), {"file": bad}).status_code == 400
    assert api.post(url(lesson), {}).status_code == 400


@pytest.mark.parametrize("role", ["student", "teacher"])
def test_only_admin_can_upload(api, auth, lesson, media_root, role, request):
    auth(api, request.getfixturevalue(role))
    assert api.post(url(lesson), {"file": png()}).status_code == 403


def test_banner_not_writable_via_patch(api, admin_user, auth, lesson):
    auth(api, admin_user)
    api.patch(f"/api/v1/manage/lessons/{lesson.id}/", {"banner": "images/hack.webp"}, format="json")
    lesson.refresh_from_db()
    assert lesson.banner == ""


def test_banner_visible_only_to_teacher(api, student, teacher, auth, lesson):
    before = content_version()
    Lesson.objects.filter(pk=lesson.pk).update(banner="images/lesson_banner.webp")
    assert content_version() != before  # o'qituvchi ilovasi qayta yuklaydi

    def first_row(user):
        auth(api, user)
        rows = api.get("/api/v1/lessons/").json()
        return (rows["results"] if isinstance(rows, dict) else rows)[0]

    assert first_row(teacher)["banner"] == "images/lesson_banner.webp"
    assert "banner" not in first_row(student)
    auth(api, student)
    assert "banner" not in api.get(f"/api/v1/lessons/{lesson.id}/").json()


def test_deleting_lesson_removes_banner_file(api, admin_user, auth, lesson, media_root):
    auth(api, admin_user)
    path = api.post(url(lesson), {"file": png()}).data["banner"]
    assert api.delete(f"/api/v1/manage/lessons/{lesson.id}/").status_code == 204
    assert not (media_root / path).exists()
