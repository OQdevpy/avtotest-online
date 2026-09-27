import pytest

pytestmark = pytest.mark.django_db


def blits_questions(blits):
    return [item.question for item in blits.items.select_related("question")]


def correct_id(question):
    return question.answers.get(is_true=True).id


def wrong_id(question):
    return question.answers.filter(is_true=False).first().id


def test_requires_auth(api, blits):
    assert api.post("/api/v1/progress/blits-results/", {}, format="json").status_code == 401


def test_score_computed_on_server(api, student, auth, blits):
    questions = blits_questions(blits)
    auth(api, student)
    response = api.post("/api/v1/progress/blits-results/", {
        "blits": blits.id,
        "score": 999,
        "items": [
            {"question": questions[0].id, "answer": correct_id(questions[0])},
            {"question": questions[1].id, "answer": wrong_id(questions[1])},
            {"question": questions[2].id, "answer": None},
        ],
    }, format="json")
    assert response.status_code == 201
    assert response.json()["score"] == 1
    assert response.json()["total"] == 3


def test_records_mistake(api, student, auth, blits):
    from apps.progress.models import Mistake

    questions = blits_questions(blits)
    auth(api, student)
    api.post("/api/v1/progress/blits-results/", {
        "blits": blits.id,
        "items": [{"question": questions[0].id, "answer": wrong_id(questions[0])}],
    }, format="json")
    mistake = Mistake.objects.get(user=student, question=questions[0])
    assert mistake.wrong_count == 1
    assert not mistake.resolved


def test_records_question_attempt(api, student, auth, blits):
    from apps.progress.models import QuestionAttempt

    questions = blits_questions(blits)
    auth(api, student)
    api.post("/api/v1/progress/blits-results/", {
        "blits": blits.id,
        "items": [{"question": questions[0].id, "answer": correct_id(questions[0])}],
    }, format="json")
    assert QuestionAttempt.objects.filter(user=student, is_correct=True).count() == 1


def test_list_returns_only_own_results(api, student, other_student, auth, blits):
    from apps.progress.models import BlitsResult

    BlitsResult.objects.create(user=student, blits=blits, score=1, total=3)
    BlitsResult.objects.create(user=other_student, blits=blits, score=2, total=3)
    auth(api, student)
    body = api.get("/api/v1/progress/blits-results/").json()
    assert body["count"] == 1
    assert body["results"][0]["score"] == 1


def test_reset_clears_blits_results(api, student, auth, blits):
    from apps.progress.models import BlitsResult

    BlitsResult.objects.create(user=student, blits=blits, score=1, total=3)
    auth(api, student)
    api.post("/api/v1/progress/reset/")
    assert not BlitsResult.objects.filter(user=student).exists()
