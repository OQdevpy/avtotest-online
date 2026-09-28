"""import_content: `--media` (rasmlar faqat WebP) va `--prune` (manbada yo'q savollarni olib tashlash)."""

import json
from pathlib import Path

import pytest
from django.core.management import CommandError, call_command
from PIL import Image

from apps.content.models import Answer, Question

pytestmark = pytest.mark.django_db


def _png(path: Path, color="red"):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), color).save(path)


def _dump(tmp_path, questions, answers=()):
    db = tmp_path / "db"
    db.mkdir(exist_ok=True)
    files = {
        "sections": [{"id": 1, "name_uz": "B", "tartib": 1}],
        "lessons": [{"id": 1, "section_id": 1, "name_uz": "D", "tartib": 1}],
        "questions": questions,
        "answers": list(answers),
    }
    for name, rows in files.items():
        (db / f"{name}.json").write_text(json.dumps(rows), encoding="utf-8")
    return db


def _q(pk, **extra):
    return {"id": pk, "lesson_id": 1, "question_uz": f"S{pk}", "question_ru": "", "question_cry": "",
            "image": "", "description_image": "", "tartib": pk, "is_in_web": False, **extra}


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    """Har bir test vaqtinchalik media papkada ishlaydi — `--prune` haqiqiy
    `backend/media` ni hech qachon o'chirib yubormasin."""
    settings.MEDIA_ROOT = str(tmp_path / "backend_media")
    return Path(settings.MEDIA_ROOT)


def test_media_converts_raster_refs_to_webp(tmp_path, media_root):
    src = tmp_path / "public_media"
    _png(src / "images/a.png")
    Image.new("RGB", (8, 8), "blue").save(src / "images/d.jpg")
    db = _dump(tmp_path, [_q(1, image="images/a.png", description_image="images/d.jpg")])

    call_command("import_content", path=str(db), media=str(src))

    q = Question.objects.get(pk=1)
    assert q.image.endswith(".webp") and q.explanation_image.endswith(".webp")
    assert (media_root / q.image).exists() and (media_root / q.explanation_image).exists()
    assert not [p for p in media_root.rglob("*") if p.suffix in {".png", ".jpg"}]


def test_media_is_idempotent(tmp_path, media_root):
    src = tmp_path / "public_media"
    _png(src / "images/a.png")
    db = _dump(tmp_path, [_q(1, image="images/a.png")])

    call_command("import_content", path=str(db), media=str(src))
    first = Question.objects.get(pk=1).image
    call_command("import_content", path=str(db), media=str(src))

    assert Question.objects.get(pk=1).image == first
    assert len(list((media_root / "images").glob("*.webp"))) == 1


def test_media_changed_source_gets_new_name(tmp_path, media_root):
    src = tmp_path / "public_media"
    _png(src / "images/a.png", "red")
    db = _dump(tmp_path, [_q(1, image="images/a.png")])
    call_command("import_content", path=str(db), media=str(src))
    first = Question.objects.get(pk=1).image

    _png(src / "images/a.png", "green")
    call_command("import_content", path=str(db), media=str(src))

    assert Question.objects.get(pk=1).image != first


def test_media_dry_run_writes_no_files(tmp_path, media_root):
    src = tmp_path / "public_media"
    _png(src / "images/a.png")
    db = _dump(tmp_path, [_q(1, image="images/a.png")])

    call_command("import_content", path=str(db), media=str(src), dry_run=True)

    assert not media_root.exists() or not list(media_root.rglob("*.webp"))
    assert Question.objects.count() == 0


def test_webp_refs_are_kept_as_is(tmp_path, media_root):
    db = _dump(tmp_path, [_q(1, image="images/x.webp")])
    call_command("import_content", path=str(db), media=str(tmp_path))
    assert Question.objects.get(pk=1).image == "images/x.webp"


def test_without_prune_extra_question_is_kept(tmp_path, lesson, make_question):
    extra = make_question(lesson, "Ortiqcha", order=99)
    db = _dump(tmp_path, [_q(500)])
    call_command("import_content", path=str(db))
    assert Question.objects.filter(pk=extra.pk).exists()


def test_prune_removes_questions_missing_from_source(tmp_path, lesson, make_question):
    extra = make_question(lesson, "Ortiqcha", order=99)
    db = _dump(tmp_path, [_q(500)])
    call_command("import_content", path=str(db), prune=True)
    assert not Question.objects.filter(pk=extra.pk).exists()
    assert Question.objects.filter(pk=500).exists()


def test_prune_removes_stray_answers_of_imported_questions(tmp_path):
    db = _dump(tmp_path, [_q(1)], [{"id": 10, "question_id": 1, "answer_uz": "A", "is_true": True}])
    call_command("import_content", path=str(db))
    Answer.objects.create(pk=11, question_id=1, text_uz="Ortiqcha javob", is_true=False, order=5)
    call_command("import_content", path=str(db), prune=True)
    assert list(Answer.objects.filter(question_id=1).values_list("pk", flat=True)) == [10]


def test_prune_refuses_empty_questions_file(tmp_path, lesson, make_question):
    make_question(lesson, "Saqlanadi", order=1)
    db = _dump(tmp_path, [])
    with pytest.raises(CommandError):
        call_command("import_content", path=str(db), prune=True)
    assert Question.objects.count() == 1


# --- --prune: dars, bo'lim, blits, bilet va yetim rasm fayllari ------------------

def _dump_full(tmp_path, blits=(), variants=()):
    db = _dump(tmp_path, [_q(500)])
    (db / "blits.json").write_text(json.dumps(list(blits)), encoding="utf-8")
    (db / "variants.json").write_text(json.dumps(list(variants)), encoding="utf-8")
    return db


def test_prune_removes_lessons_and_sections_missing_from_source(tmp_path, section):
    from apps.content.models import Lesson, Section

    extra_section = Section.objects.create(pk=77, name_uz="Ortiqcha bo'lim", order=9)
    extra_lesson = Lesson.objects.create(pk=88, section=extra_section, name_uz="Ortiqcha dars", order=9)
    db = _dump(tmp_path, [_q(500)])
    call_command("import_content", path=str(db), prune=True)
    assert not Lesson.objects.filter(pk=extra_lesson.pk).exists()
    assert not Section.objects.filter(pk=extra_section.pk).exists()
    assert Lesson.objects.filter(pk=1).exists() and Section.objects.filter(pk=1).exists()


def test_prune_removes_blits_and_tickets_missing_from_source(tmp_path):
    from apps.content.models import Blits, Ticket

    Blits.objects.create(pk=50, name_uz="Eski blits", order=1)
    Ticket.objects.create(number=99)
    db = _dump_full(tmp_path, blits=[{"id": 4, "name_uz": "Yangi", "question_ids": [500]}],
                    variants=[{"var_id": 0, "question_ids": [500]}])
    call_command("import_content", path=str(db), prune=True)
    assert list(Blits.objects.values_list("pk", flat=True)) == [4]
    assert list(Ticket.objects.values_list("number", flat=True)) == [1]


def test_prune_keeps_blits_when_source_file_absent(tmp_path):
    """blits.json umuman berilmagan bo'lsa, mavjud blitslar tegilmaydi."""
    from apps.content.models import Blits

    Blits.objects.create(pk=50, name_uz="Saqlanadi", order=1)
    db = _dump(tmp_path, [_q(500)])
    call_command("import_content", path=str(db), prune=True)
    assert Blits.objects.filter(pk=50).exists()


def test_prune_removes_unreferenced_image_files(tmp_path, media_root):
    src = tmp_path / "public_media"
    _png(src / "images/a.png")
    db = _dump(tmp_path, [_q(500, image="images/a.png")])
    stray = media_root / "images" / "eski_yetim.webp"
    stray.parent.mkdir(parents=True, exist_ok=True)
    stray.write_bytes(b"x")
    root_file = media_root / "default_image.jpg"
    root_file.write_bytes(b"y")

    call_command("import_content", path=str(db), media=str(src), prune=True)

    used = Question.objects.get(pk=500).image
    assert (media_root / used).exists()
    assert not stray.exists()
    assert root_file.exists()  # images/ dan tashqaridagi fayllarga tegilmaydi


def test_prune_dry_run_keeps_files_and_rows(tmp_path, media_root):
    stray = media_root / "images" / "eski_yetim.webp"
    stray.parent.mkdir(parents=True, exist_ok=True)
    stray.write_bytes(b"x")
    db = _dump(tmp_path, [_q(500)])
    call_command("import_content", path=str(db), prune=True, dry_run=True)
    assert stray.exists()


def test_prune_never_deletes_media_when_db_has_no_images(tmp_path, media_root):
    """Bazada birorta ham savol rasmi bo'lmasa, hamma fayl 'yetim' ko'rinadi —
    bu xato holat, shuning uchun hech narsa o'chirilmaydi."""
    keep = media_root / "images" / "muhim.webp"
    keep.parent.mkdir(parents=True, exist_ok=True)
    keep.write_bytes(b"x")
    db = _dump(tmp_path, [_q(500)])  # rasmsiz savol
    call_command("import_content", path=str(db), prune=True)
    assert keep.exists()


def test_prune_keeps_tickets_present_in_source(tmp_path):
    """Manbada bor bilet o'chirilib qayta yaratilmasligi kerak (id o'zgarmaydi)."""
    from apps.content.models import Ticket

    keep = Ticket.objects.create(number=1)
    db = _dump_full(tmp_path, variants=[{"var_id": 0, "question_ids": [500]}])
    call_command("import_content", path=str(db), prune=True)
    assert Ticket.objects.get(number=1).pk == keep.pk
