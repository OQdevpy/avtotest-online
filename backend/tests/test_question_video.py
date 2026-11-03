"""Savol videosi: yuklash, URL va o'chirish."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

pytestmark = pytest.mark.django_db


@pytest.fixture
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


def upload_video(api, question, name="izoh.mp4", content_type="video/mp4"):
    return api.post(f"/api/v1/manage/questions/{question.id}/video/",
                    {"file": SimpleUploadedFile(name, b"\x00\x00\x00\x18ftypmp42", content_type)})


def test_video_upload_keeps_extension(api, admin_user, auth, question, media_root):
    auth(api, admin_user)
    response = upload_video(api, question)
    assert response.status_code == 200
    assert response.json()["video"].startswith("videos/")
    assert response.json()["video"].endswith(".mp4")
    question.refresh_from_db()
    assert (media_root / question.video).exists()


def test_video_reupload_removes_old_file(api, admin_user, auth, question, media_root):
    auth(api, admin_user)
    first = upload_video(api, question).json()["video"]
    upload_video(api, question, name="yangi.mov", content_type="video/quicktime")
    question.refresh_from_db()
    assert question.video.endswith(".mov")
    assert not (media_root / first).exists()


def test_video_rejects_unsupported_extension(api, admin_user, auth, question, media_root):
    auth(api, admin_user)
    response = upload_video(api, question, name="x.exe", content_type="application/octet-stream")
    assert response.status_code == 400


def test_student_cannot_upload_video(api, student, auth, question, media_root):
    auth(api, student)
    assert upload_video(api, question).status_code == 403


def test_lesson_detail_has_video_url(api, student, auth, question):
    question.video = "videos/q1.mp4"
    question.save(update_fields=["video"])
    auth(api, student)
    row = api.get(f"/api/v1/lessons/{question.lesson_id}/").json()["questions"][0]
    assert row["video"] == "videos/q1.mp4"
    assert row["video_url"].endswith("/media/videos/q1.mp4")


def test_lesson_detail_video_url_null_without_video(api, student, auth, question):
    auth(api, student)
    row = api.get(f"/api/v1/lessons/{question.lesson_id}/").json()["questions"][0]
    assert row["video_url"] is None


def test_staff_can_clear_video(api, admin_user, auth, question):
    question.video = "videos/q1.mp4"
    question.save(update_fields=["video"])
    auth(api, admin_user)
    response = api.patch(f"/api/v1/manage/questions/{question.id}/", {"video": ""}, format="json")
    assert response.status_code == 200, response.data
    question.refresh_from_db()
    assert question.video == ""
