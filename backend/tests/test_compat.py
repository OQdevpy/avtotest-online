"""Eski frontlar (web, darslik) uchun maydon taxalluslari.

Taxalluslar faqat `?compat=1` so'ralganda qo'shiladi — mobil javoblari
semirmaydi.
"""

import pytest

pytestmark = pytest.mark.django_db


def first_question(api, url):
    return api.get(url).json()["results"][0]


def test_aliases_absent_without_compat_flag(api, student, auth, question):
    auth(api, student)
    row = first_question(api, "/api/v1/questions/")
    assert "question_uz" not in row
    assert "tartib" not in row
    assert row["text"] == question.text_uz


def test_aliases_present_with_compat_flag(api, student, auth, question):
    auth(api, student)
    row = first_question(api, "/api/v1/questions/?compat=1")
    assert row["question_uz"] == question.text_uz
    assert row["question_ru"] == question.text_ru
    assert row["question_cry"] == question.text_cry
    assert row["tartib"] == question.order


def test_compat_keeps_new_fields_too(api, student, auth, question):
    auth(api, student)
    row = first_question(api, "/api/v1/questions/?compat=1")
    assert row["text"] == question.text_uz
    assert row["id"] == question.id


def test_answer_aliases_present_with_compat_flag(api, student, auth, question):
    auth(api, student)
    row = first_question(api, "/api/v1/questions/?compat=1")
    answer = row["answers"][0]
    correct = question.answers.order_by("order").first()
    assert answer["answer_uz"] == correct.text_uz
    assert answer["answer_ru"] == correct.text_ru
    assert answer["answer_cry"] == correct.text_cry
    assert answer["tartib"] == correct.order


def test_answer_aliases_absent_without_flag(api, student, auth, question):
    auth(api, student)
    assert "answer_uz" not in first_question(api, "/api/v1/questions/")["answers"][0]


def test_compat_does_not_reveal_is_true(api, student, auth, question):
    auth(api, student)
    assert "is_true" not in first_question(api, "/api/v1/questions/?compat=1")["answers"][0]


def test_compat_works_in_lesson_detail(api, student, auth, question):
    auth(api, student)
    body = api.get(f"/api/v1/lessons/{question.lesson_id}/?compat=1").json()
    assert body["questions"][0]["question_uz"] == question.text_uz


def test_compat_works_in_ticket_detail(api, student, auth, ticket):
    auth(api, student)
    body = api.get(f"/api/v1/tickets/{ticket.number}/?compat=1").json()
    assert "question_uz" in body["questions"][0]


def test_compat_zero_is_not_enabled(api, student, auth, question):
    auth(api, student)
    assert "question_uz" not in first_question(api, "/api/v1/questions/?compat=0")
