import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from PIL import Image

pytestmark = pytest.mark.django_db


@pytest.fixture
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    (tmp_path / "images").mkdir()
    return tmp_path


def png_bytes(color="red"):
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), color).save(buffer, "PNG")
    return buffer.getvalue()


def upload(api, question, data, field="image"):
    return api.post(f"/api/v1/manage/questions/{question.id}/{field}/", data)


# --- Yuklash ----------------------------------------------------------------

def test_uploaded_png_is_stored_as_webp(api, admin_user, auth, question, media_root):
    auth(api, admin_user)
    response = upload(api, question,
                      {"file": SimpleUploadedFile("a.png", png_bytes(), "image/png")})
    assert response.status_code == 200
    assert response.json()["image"].endswith(".webp")
    question.refresh_from_db()
    assert (media_root / question.image).exists()


def test_uploaded_file_is_really_webp(api, admin_user, auth, question, media_root):
    auth(api, admin_user)
    upload(api, question, {"file": SimpleUploadedFile("a.png", png_bytes(), "image/png")})
    question.refresh_from_db()
    with Image.open(media_root / question.image) as img:
        assert img.format == "WEBP"


def test_non_image_upload_rejected(api, admin_user, auth, question, media_root):
    auth(api, admin_user)
    response = upload(api, question,
                      {"file": SimpleUploadedFile("a.txt", b"salom", "text/plain")})
    assert response.status_code == 400


def test_missing_file_rejected(api, admin_user, auth, question, media_root):
    auth(api, admin_user)
    assert upload(api, question, {}).status_code == 400


def test_student_cannot_upload(api, student, auth, question, media_root):
    auth(api, student)
    response = upload(api, question,
                      {"file": SimpleUploadedFile("a.png", png_bytes(), "image/png")})
    assert response.status_code == 403


def test_teacher_cannot_upload(api, teacher, auth, question, media_root):
    auth(api, teacher)
    response = upload(api, question,
                      {"file": SimpleUploadedFile("a.png", png_bytes(), "image/png")})
    assert response.status_code == 403


def test_replacing_image_removes_previous_file(api, admin_user, auth, question,
                                               media_root):
    auth(api, admin_user)
    upload(api, question, {"file": SimpleUploadedFile("a.png", png_bytes("red"), "image/png")})
    question.refresh_from_db()
    first = media_root / question.image
    upload(api, question, {"file": SimpleUploadedFile("b.png", png_bytes("blue"), "image/png")})
    question.refresh_from_db()
    second = media_root / question.image
    assert first != second
    assert not first.exists()
    assert second.exists()


def test_audio_upload_keeps_extension(api, admin_user, auth, question, media_root):
    auth(api, admin_user)
    response = upload(api, question,
                      {"file": SimpleUploadedFile("izoh.mp3", b"ID3fake", "audio/mpeg")},
                      field="audio")
    assert response.status_code == 200
    assert response.json()["audio"].endswith(".mp3")
    question.refresh_from_db()
    assert (media_root / question.audio).exists()


def test_audio_rejects_unsupported_extension(api, admin_user, auth, question, media_root):
    auth(api, admin_user)
    response = upload(api, question,
                      {"file": SimpleUploadedFile("x.exe", b"MZ", "application/octet-stream")},
                      field="audio")
    assert response.status_code == 400


# --- Ommaviy o'girish -------------------------------------------------------

@pytest.fixture
def question_with_png(question, media_root):
    path = media_root / "images" / "eski.png"
    path.write_bytes(png_bytes())
    question.image = "images/eski.png"
    question.save(update_fields=["image"])
    return question


def test_bulk_command_converts_png_and_updates_path(question_with_png, media_root):
    call_command("convert_images_to_webp")
    question_with_png.refresh_from_db()
    assert question_with_png.image.endswith(".webp")
    assert (media_root / question_with_png.image).exists()


def test_bulk_command_is_idempotent(question_with_png, media_root):
    call_command("convert_images_to_webp")
    question_with_png.refresh_from_db()
    first = question_with_png.image
    call_command("convert_images_to_webp")
    question_with_png.refresh_from_db()
    assert question_with_png.image == first


def test_bulk_dry_run_changes_nothing(question_with_png, media_root):
    call_command("convert_images_to_webp", dry_run=True)
    question_with_png.refresh_from_db()
    assert question_with_png.image == "images/eski.png"


def test_bulk_command_converts_explanation_image(question, media_root):
    path = media_root / "images" / "izoh.png"
    path.write_bytes(png_bytes())
    question.explanation_image = "images/izoh.png"
    question.save(update_fields=["explanation_image"])
    call_command("convert_images_to_webp")
    question.refresh_from_db()
    assert question.explanation_image.endswith(".webp")


def test_bulk_command_skips_missing_file(question, media_root):
    question.image = "images/yoq.png"
    question.save(update_fields=["image"])
    call_command("convert_images_to_webp")
    question.refresh_from_db()
    assert question.image == "images/yoq.png"
