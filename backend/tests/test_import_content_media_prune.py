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


@pytest.fixture
def media_root(settings, tmp_path):
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
