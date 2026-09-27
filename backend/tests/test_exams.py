from datetime import timedelta

import pytest
from django.utils import timezone

from apps.exams.models import ExamSession
from apps.progress.models import ExamAttempt

pytestmark = pytest.mark.django_db


def start(api, mode=20):
    return api.post("/api/v1/exams/start/", {"mode": mode}, format="json")


def correct_answer_id(question_payload):
    """Serverdan kelgan savol uchun to'g'ri javob id'si (bazadan olinadi)."""
    from apps.content.models import Answer

    return Answer.objects.get(question_id=question_payload["id"], is_true=True).id


# --- start ------------------------------------------------------------------

def test_start_requires_auth(api, many_questions):
    assert start(api).status_code == 401


def test_start_returns_twenty_questions_and_pass_score(api, student, auth, many_questions):
    auth(api, student)
    body = start(api, 20).json()
    assert len(body["questions"]) == 20
    assert body["pass_score"] == 18
    assert body["minutes"] == 25
    assert body["ends_at"]


def test_start_rejects_unknown_mode(api, student, auth, many_questions):
    auth(api, student)
    assert start(api, 33).status_code == 400


def test_start_hides_correct_answer(api, student, auth, many_questions):
    auth(api, student)
    body = start(api).json()
    assert "is_true" not in body["questions"][0]["answers"][0]


def test_start_records_session_questions(api, student, auth, many_questions):
    auth(api, student)
    session_id = start(api).json()["id"]
    assert ExamSession.objects.get(pk=session_id).items.count() == 20


def test_start_fails_when_not_enough_questions(api, student, auth, question):
    auth(api, student)
    assert start(api, 50).status_code == 400


# --- answer -----------------------------------------------------------------

def test_answer_is_saved(api, student, auth, many_questions):
    auth(api, student)
    body = start(api).json()
    first = body["questions"][0]
    response = api.post(f"/api/v1/exams/{body['id']}/answer/",
                        {"question": first["id"], "answer": correct_answer_id(first)},
                        format="json")
    assert response.status_code == 200
    item = ExamSession.objects.get(pk=body["id"]).items.get(question_id=first["id"])
    assert item.answer_id == correct_answer_id(first)


def test_answer_rejects_question_outside_session(api, student, auth, many_questions,
                                                 lesson, make_question):
    auth(api, student)
    body = start(api).json()
    outsider = make_question(lesson, "Tashqi savol", order=99)
    response = api.post(f"/api/v1/exams/{body['id']}/answer/",
                        {"question": outsider.id, "answer": None}, format="json")
    assert response.status_code == 400


def test_answer_after_deadline_returns_409(api, student, auth, many_questions):
    auth(api, student)
    body = start(api).json()
    ExamSession.objects.filter(pk=body["id"]).update(
        ends_at=timezone.now() - timedelta(seconds=1)
    )
    first = body["questions"][0]
    response = api.post(f"/api/v1/exams/{body['id']}/answer/",
                        {"question": first["id"], "answer": correct_answer_id(first)},
                        format="json")
    assert response.status_code == 409


def test_cannot_answer_another_users_session(api, student, other_student, auth,
                                             many_questions):
    auth(api, student)
    body = start(api).json()
    api.credentials()
    auth(api, other_student)
    first = body["questions"][0]
    response = api.post(f"/api/v1/exams/{body['id']}/answer/",
                        {"question": first["id"], "answer": None}, format="json")
    assert response.status_code == 404


# --- finish -----------------------------------------------------------------

def answer_all(api, body, correct=True):
    for question in body["questions"]:
        answer = correct_answer_id(question) if correct else None
        api.post(f"/api/v1/exams/{body['id']}/answer/",
                 {"question": question["id"], "answer": answer}, format="json")


def test_finish_grades_on_server(api, student, auth, many_questions):
    auth(api, student)
    body = start(api).json()
    answer_all(api, body, correct=True)
    result = api.post(f"/api/v1/exams/{body['id']}/finish/").json()
    assert result["score"] == 20
    assert result["passed"] is True


def test_finish_ignores_client_supplied_score(api, student, auth, many_questions):
    auth(api, student)
    body = start(api).json()
    answer_all(api, body, correct=False)
    result = api.post(f"/api/v1/exams/{body['id']}/finish/",
                      {"score": 20}, format="json").json()
    assert result["score"] == 0
    assert result["passed"] is False


def test_finish_creates_exam_attempt(api, student, auth, many_questions):
    auth(api, student)
    body = start(api).json()
    answer_all(api, body)
    api.post(f"/api/v1/exams/{body['id']}/finish/")
    assert ExamAttempt.objects.filter(user=student).count() == 1


def test_finish_records_mistakes(api, student, auth, many_questions):
    from apps.progress.models import Mistake

    auth(api, student)
    body = start(api).json()
    answer_all(api, body, correct=False)
    api.post(f"/api/v1/exams/{body['id']}/finish/")
    assert Mistake.objects.filter(user=student, wrong_count__gt=0).count() == 20


# Review Focus #2
def test_finish_twice_is_idempotent(api, student, auth, many_questions):
    auth(api, student)
    body = start(api).json()
    answer_all(api, body)
    first = api.post(f"/api/v1/exams/{body['id']}/finish/").json()
    second = api.post(f"/api/v1/exams/{body['id']}/finish/")
    assert second.status_code == 409
    assert ExamAttempt.objects.filter(user=student).count() == 1
    session = ExamSession.objects.get(pk=body["id"])
    assert session.score == first["score"]


def test_finish_works_after_deadline(api, student, auth, many_questions):
    auth(api, student)
    body = start(api).json()
    answer_all(api, body)
    ExamSession.objects.filter(pk=body["id"]).update(
        ends_at=timezone.now() - timedelta(seconds=1)
    )
    assert api.post(f"/api/v1/exams/{body['id']}/finish/").status_code == 200


def test_finish_counts_unanswered_as_wrong(api, student, auth, many_questions):
    auth(api, student)
    body = start(api).json()
    first = body["questions"][0]
    api.post(f"/api/v1/exams/{body['id']}/answer/",
             {"question": first["id"], "answer": correct_answer_id(first)}, format="json")
    result = api.post(f"/api/v1/exams/{body['id']}/finish/").json()
    assert result["score"] == 1
    assert result["total"] == 20


# --- ko'rish -----------------------------------------------------------------

def test_detail_returns_result(api, student, auth, many_questions):
    auth(api, student)
    body = start(api).json()
    api.post(f"/api/v1/exams/{body['id']}/finish/")
    assert api.get(f"/api/v1/exams/{body['id']}/").status_code == 200


def test_cannot_open_another_users_session(api, student, other_student, auth,
                                          many_questions):
    auth(api, student)
    session_id = start(api).json()["id"]
    api.credentials()
    auth(api, other_student)
    assert api.get(f"/api/v1/exams/{session_id}/").status_code == 404


def test_list_returns_own_sessions_only(api, student, other_student, auth,
                                        many_questions):
    auth(api, student)
    start(api)
    api.credentials()
    auth(api, other_student)
    start(api)
    body = api.get("/api/v1/exams/").json()
    assert body["count"] == 1


# --- deprecated yo'llar ishlashda davom etadi -------------------------------

def test_deprecated_exam_generate_still_works(api, student, auth, many_questions):
    auth(api, student)
    response = api.get("/api/v1/exam/generate/?count=20")
    assert response.status_code == 200
    assert len(response.json()["questions"]) == 20


def test_deprecated_exam_attempts_post_still_works(api, student, auth, many_questions):
    auth(api, student)
    items = [{"question": q.id, "answer": None} for q in many_questions[:20]]
    response = api.post("/api/v1/progress/exam-attempts/",
                        {"items": items}, format="json")
    assert response.status_code == 201


# Task 6 dan ko'chirilgan — Review Focus #1, imtihon yo'li
def test_unpublished_never_appears_in_exam(api, student, auth, lesson, make_question):
    for index in range(20):
        make_question(lesson, f"Ko'rinadigan {index}", order=index)
    for index in range(20):
        make_question(lesson, f"Yashirin {index}", order=100 + index, published=False)
    auth(api, student)
    for _ in range(5):
        body = start(api).json()
        assert all(not q["text"].startswith("Yashirin") for q in body["questions"])
