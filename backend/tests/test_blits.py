import pytest

pytestmark = pytest.mark.django_db


def test_blits_list_returns_name_in_requested_language(api, student, auth, blits):
    auth(api, student)
    rows = api.get("/api/v1/blits/?lang=kr").json()["results"]
    assert rows[0]["name"] == blits.name_cry


def test_blits_list_defaults_to_uzbek(api, student, auth, blits):
    auth(api, student)
    rows = api.get("/api/v1/blits/").json()["results"]
    assert rows[0]["name"] == blits.name_uz


def test_blits_list_reports_question_count(api, student, auth, blits):
    auth(api, student)
    assert api.get("/api/v1/blits/").json()["results"][0]["question_count"] == 3


def test_blits_list_hides_inactive(api, student, auth, blits):
    from apps.content.models import Blits

    Blits.objects.filter(pk=blits.pk).update(is_active=False)
    auth(api, student)
    assert api.get("/api/v1/blits/").json()["results"] == []


def test_blits_detail_returns_questions_in_order(api, student, auth, blits):
    auth(api, student)
    body = api.get(f"/api/v1/blits/{blits.id}/").json()
    assert [q["text"] for q in body["questions"]] == [
        "Blits savol 0", "Blits savol 1", "Blits savol 2",
    ]


def test_blits_detail_hides_correct_answer(api, student, auth, blits):
    auth(api, student)
    body = api.get(f"/api/v1/blits/{blits.id}/").json()
    assert "is_true" not in body["questions"][0]["answers"][0]


def test_blits_detail_study_mode_shows_correct_answer(api, student, auth, blits):
    auth(api, student)
    body = api.get(f"/api/v1/blits/{blits.id}/?mode=study").json()
    assert "is_true" in body["questions"][0]["answers"][0]


def test_teacher_sees_correct_answer_in_blits(api, teacher, auth, blits):
    auth(api, teacher)
    body = api.get(f"/api/v1/blits/{blits.id}/").json()
    assert "is_true" in body["questions"][0]["answers"][0]


def test_blits_requires_auth(api, blits):
    assert api.get("/api/v1/blits/").status_code == 401


# Task 6 dan ko'chirilgan — Review Focus #1, blits yo'li
def test_unpublished_hidden_from_blits_detail(api, student, auth, blits, lesson,
                                              make_question):
    from apps.content.models import BlitsQuestion

    hidden = make_question(lesson, "Yashirin blits savoli", order=9, published=False)
    BlitsQuestion.objects.create(blits=blits, question=hidden, order=9)
    auth(api, student)
    body = api.get(f"/api/v1/blits/{blits.id}/").json()
    texts = [q["text"] for q in body["questions"]]
    assert "Yashirin blits savoli" not in texts
    assert len(texts) == 3


def test_teacher_sees_unpublished_in_blits_detail(api, teacher, auth, blits, lesson,
                                                  make_question):
    from apps.content.models import BlitsQuestion

    hidden = make_question(lesson, "Yashirin blits savoli", order=9, published=False)
    BlitsQuestion.objects.create(blits=blits, question=hidden, order=9)
    auth(api, teacher)
    body = api.get(f"/api/v1/blits/{blits.id}/").json()
    assert "Yashirin blits savoli" in [q["text"] for q in body["questions"]]


def test_blits_question_count_excludes_unpublished(api, student, auth, blits, lesson,
                                                   make_question):
    from apps.content.models import BlitsQuestion

    hidden = make_question(lesson, "Yashirin", order=9, published=False)
    BlitsQuestion.objects.create(blits=blits, question=hidden, order=9)
    auth(api, student)
    assert api.get("/api/v1/blits/").json()["results"][0]["question_count"] == 3
