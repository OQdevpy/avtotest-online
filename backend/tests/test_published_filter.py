"""Nashr etilmagan savol o'quvchiga hech bir yo'l orqali ko'rinmasligi kerak.

Review Focus #1 — dars, bilet, qidiruv (blits va imtihon Task 7/11 da).
"""

import pytest

pytestmark = pytest.mark.django_db


@pytest.fixture
def hidden(lesson, make_question):
    return make_question(lesson, "Yashirin savol", order=5, published=False)


def _texts(payload):
    return [q["text"] for q in payload]


def test_unpublished_hidden_from_lesson_detail(api, student, auth, question, hidden):
    auth(api, student)
    body = api.get(f"/api/v1/lessons/{question.lesson_id}/").json()
    assert "Yashirin savol" not in _texts(body["questions"])
    assert "Nechta guruh bor?" in _texts(body["questions"])


def test_teacher_sees_unpublished_in_lesson_detail(api, teacher, auth, question, hidden):
    auth(api, teacher)
    body = api.get(f"/api/v1/lessons/{question.lesson_id}/").json()
    assert "Yashirin savol" in _texts(body["questions"])


def test_admin_sees_unpublished_in_lesson_detail(api, admin_user, auth, question, hidden):
    auth(api, admin_user)
    body = api.get(f"/api/v1/lessons/{question.lesson_id}/").json()
    assert "Yashirin savol" in _texts(body["questions"])


def test_unpublished_hidden_from_ticket_detail(api, student, auth, ticket, lesson,
                                               make_question):
    from apps.content.models import TicketQuestion

    hidden = make_question(lesson, "Yashirin bilet savoli", order=9, published=False)
    TicketQuestion.objects.create(ticket=ticket, question=hidden, order=1)
    auth(api, student)
    body = api.get(f"/api/v1/tickets/{ticket.number}/").json()
    assert "Yashirin bilet savoli" not in _texts(body["questions"])


def test_unpublished_hidden_from_topic_detail(api, student, auth, lesson, make_question):
    """`Mavzular` = `Darslar` — /topics/{lesson.id}/ ham dars filtriga bo'ysunadi."""
    make_question(lesson, "Ko'rinadigan", order=1)
    make_question(lesson, "Yashirin mavzu savoli", order=2, published=False)
    auth(api, student)
    body = api.get(f"/api/v1/topics/{lesson.id}/").json()
    assert "Yashirin mavzu savoli" not in _texts(body["questions"])


def test_new_question_defaults_to_unpublished(lesson):
    from apps.content.models import Question

    question = Question.objects.create(lesson=lesson, text_uz="Yangi")
    assert question.is_published is False


def test_is_in_web_defaults_to_false(lesson):
    from apps.content.models import Question

    assert Question.objects.create(lesson=lesson, text_uz="Yangi").is_in_web is False


def test_published_manager_excludes_unpublished(question, hidden):
    from apps.content.models import Question

    ids = set(Question.published.values_list("id", flat=True))
    assert question.id in ids
    assert hidden.id not in ids


# Spec §6: to'g'ri javob test rejimida yopiq, o'rganishda va teacher/admin uchun ochiq.
# Dars ekrani — o'rganish rejimi (mobil ilova uni `?mode=study` siz chaqiradi),
# shuning uchun kalit ochiq. Yopiladigan joylar — bilet, blits va imtihon.

def test_student_does_not_see_is_true_in_ticket_test_mode(api, student, auth, ticket):
    auth(api, student)
    body = api.get(f"/api/v1/tickets/{ticket.number}/").json()
    assert "is_true" not in body["questions"][0]["answers"][0]


def test_student_sees_is_true_in_ticket_study_mode(api, student, auth, ticket):
    auth(api, student)
    body = api.get(f"/api/v1/tickets/{ticket.number}/?mode=study").json()
    assert "is_true" in body["questions"][0]["answers"][0]


def test_student_sees_is_true_in_lesson_study_screen(api, student, auth, question):
    auth(api, student)
    body = api.get(f"/api/v1/lessons/{question.lesson_id}/").json()
    assert "is_true" in body["questions"][0]["answers"][0]


def test_teacher_sees_is_true_without_study_mode(api, teacher, auth, question):
    auth(api, teacher)
    body = api.get(f"/api/v1/lessons/{question.lesson_id}/").json()
    assert "is_true" in body["questions"][0]["answers"][0]


def test_teacher_sees_is_true_in_ticket_detail(api, teacher, auth, ticket):
    auth(api, teacher)
    body = api.get(f"/api/v1/tickets/{ticket.number}/").json()
    assert "is_true" in body["questions"][0]["answers"][0]
