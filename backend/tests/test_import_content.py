from pathlib import Path

import pytest
from django.core.management import call_command

from apps.content.models import (
    Answer,
    Blits,
    BlitsQuestion,
    Lesson,
    Question,
    Section,
    Ticket,
    TicketQuestion,
)

pytestmark = pytest.mark.django_db

FIXTURE = Path(__file__).parent / "fixtures" / "admin_panel_db"


def run(**kwargs):
    call_command("import_content", path=str(FIXTURE), **kwargs)


def counts():
    return {
        "sections": Section.objects.count(),
        "lessons": Lesson.objects.count(),
        "questions": Question.objects.count(),
        "answers": Answer.objects.count(),
        "blits": Blits.objects.count(),
        "tickets": Ticket.objects.count(),
    }


# --- Yaratish ---------------------------------------------------------------

def test_creates_missing_rows(db):
    run()
    assert Section.objects.filter(pk=1).exists()
    assert Lesson.objects.filter(pk=16).exists()
    assert Question.objects.filter(pk=55).exists()
    assert Answer.objects.filter(pk=210).exists()


def test_preserves_legacy_ids(db):
    run()
    question = Question.objects.get(pk=55)
    assert question.lesson_id == 16
    assert question.lesson.section_id == 1


def test_maps_legacy_field_names(db):
    run()
    question = Question.objects.get(pk=55)
    assert question.text_uz.startswith("Yo'l belgilari")
    assert question.text_ru.startswith("Сколько")
    assert question.text_cry.startswith("Йўл")
    answer = Answer.objects.get(pk=210)
    assert answer.text_uz == "7 ta"
    assert answer.is_true is True


def test_tartib_maps_to_order(db):
    run()
    assert Lesson.objects.get(pk=17).order == 2
    assert Question.objects.get(pk=56).order == 2


def test_description_image_maps_to_explanation_image(db):
    run()
    assert Question.objects.get(pk=56).explanation_image == "images/desc_56.webp"


def test_is_in_web_is_imported(db):
    run()
    assert Question.objects.get(pk=56).is_in_web is True
    assert Question.objects.get(pk=55).is_in_web is False


def test_imported_questions_are_published(db):
    run()
    assert Question.objects.filter(is_published=True).count() == 3


def test_blits_and_question_order_preserved(db):
    run()
    blits = Blits.objects.get(pk=1)
    assert blits.name_uz == "Blits 1"
    assert [item.question_id for item in blits.items.order_by("order")] == [56, 55]


def test_variants_become_tickets(db):
    run()
    assert Ticket.objects.filter(number=1).exists()
    ticket = Ticket.objects.get(number=1)
    assert [i.question_id for i in ticket.items.order_by("order")] == [55, 56]


# --- Yangilash --------------------------------------------------------------

def test_updates_existing_row_by_id(db, section):
    existing = Question.objects.create(
        pk=55, lesson=Lesson.objects.create(pk=16, section=section, name_uz="Eski"),
        text_uz="Eski matn", is_published=True,
    )
    run()
    existing.refresh_from_db()
    assert existing.text_uz.startswith("Yo'l belgilari")


def test_row_missing_from_json_is_kept(db, lesson, make_question):
    orphan = make_question(lesson, "Faqat bazada bor", order=99)
    run()
    assert Question.objects.filter(pk=orphan.pk).exists()


def test_does_not_unpublish_existing_rows(db, section):
    lesson = Lesson.objects.create(pk=16, section=section, name_uz="Eski")
    Question.objects.create(pk=55, lesson=lesson, text_uz="Eski", is_published=True)
    run()
    assert Question.objects.get(pk=55).is_published is True


# --- Idempotentlik va dry-run -----------------------------------------------

def test_is_idempotent(db):
    run()
    first = counts()
    run()
    assert counts() == first


def test_dry_run_writes_nothing(db):
    run(dry_run=True)
    assert counts() == {"sections": 0, "lessons": 0, "questions": 0,
                        "answers": 0, "blits": 0, "tickets": 0}


def test_missing_path_raises(db):
    from django.core.management.base import CommandError

    with pytest.raises(CommandError):
        call_command("import_content", path="/yoq/bunday/papka")


def test_optional_variants_file_may_be_absent(db, tmp_path):
    import shutil

    for name in ("sections", "lessons", "questions", "answers", "blits"):
        shutil.copy(FIXTURE / f"{name}.json", tmp_path / f"{name}.json")
    call_command("import_content", path=str(tmp_path))
    assert Question.objects.count() == 3
    assert Ticket.objects.count() == 0
