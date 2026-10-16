"""`content/version/` — desktop shu bilan yangi savollarni sezadi va sanani ko'rsatadi."""

from datetime import timedelta

from django.utils import timezone

from apps.content.models import Answer, Lesson, Question, Section, Ticket, TicketQuestion

URL = "/api/v1/content/version/"


def get(api, student, auth):
    auth(api, student)
    response = api.get(URL)
    assert response.status_code == 200
    return response.json()


def test_requires_login(api, db):
    assert api.get(URL).status_code == 401


def test_updated_at_is_latest_question_or_answer_change(api, student, auth, question):
    old = timezone.now() - timedelta(days=30)
    Question.objects.update(updated_at=old)
    Answer.objects.update(updated_at=old)
    newest = timezone.now() - timedelta(days=2)
    Answer.objects.filter(pk=question.answers.first().pk).update(updated_at=newest)

    body = get(api, student, auth)
    assert body["updated_at"][:16] == newest.isoformat()[:16]


def test_version_is_stable_without_changes(api, student, auth, question):
    assert get(api, student, auth)["version"] == get(api, student, auth)["version"]


def test_version_changes_when_question_added(api, student, auth, lesson, question, make_question):
    before = get(api, student, auth)["version"]
    make_question(lesson, "Yangi savol")
    assert get(api, student, auth)["version"] != before


def test_version_changes_when_lesson_moves_to_other_section(api, student, auth, lesson, question):
    before = get(api, student, auth)["version"]
    other = Section.objects.create(name_uz="Boshqa", order=5)
    Lesson.objects.filter(pk=lesson.pk).update(section=other)  # ORM update — updated_at yo'q
    assert get(api, student, auth)["version"] != before


def test_version_changes_on_reorder_and_answer_edit(api, student, auth, question):
    v1 = get(api, student, auth)["version"]
    Question.objects.filter(pk=question.pk).update(order=99)
    v2 = get(api, student, auth)["version"]
    answer = question.answers.first()
    answer.text_uz = "Tahrirlangan"
    answer.save()
    v3 = get(api, student, auth)["version"]
    assert len({v1, v2, v3}) == 3


def test_version_changes_when_ticket_gets_question(api, student, auth, ticket, lesson, make_question):
    before = get(api, student, auth)["version"]
    TicketQuestion.objects.create(ticket=ticket, question=make_question(lesson, "B"), order=5)
    assert get(api, student, auth)["version"] != before
    Ticket.objects.filter(pk=ticket.pk).update(is_pro=True)
    assert get(api, student, auth)["version"] != before


def test_version_changes_when_question_deleted(api, student, auth, lesson, question, make_question):
    extra = make_question(lesson, "O'chiriladi")
    before = get(api, student, auth)["version"]
    extra.delete()
    assert get(api, student, auth)["version"] != before
