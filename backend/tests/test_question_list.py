import pytest

pytestmark = pytest.mark.django_db


def test_requires_auth(api, question):
    assert api.get("/api/v1/questions/").status_code == 401


def test_filters_by_lesson(api, student, auth, lesson, section, make_question):
    from apps.content.models import Lesson

    other = Lesson.objects.create(section=section, name_uz="Boshqa dars", order=2)
    make_question(lesson, "Birinchi darsdan", order=0)
    make_question(other, "Ikkinchi darsdan", order=0)
    auth(api, student)
    rows = api.get(f"/api/v1/questions/?lesson={lesson.id}").json()["results"]
    assert [r["text"] for r in rows] == ["Birinchi darsdan"]


def test_filters_by_section(api, student, auth, lesson, section, make_question):
    from apps.content.models import Section, Lesson

    other_section = Section.objects.create(name_uz="2-bo'lim", order=2)
    other_lesson = Lesson.objects.create(section=other_section, name_uz="Dars", order=1)
    make_question(lesson, "Birinchi bo'limdan", order=0)
    make_question(other_lesson, "Ikkinchi bo'limdan", order=0)
    auth(api, student)
    rows = api.get(f"/api/v1/questions/?section={section.id}").json()["results"]
    assert [r["text"] for r in rows] == ["Birinchi bo'limdan"]


def test_search_matches_uzbek_column(api, student, auth, lesson, make_question):
    make_question(lesson, "Svetofor haqida", order=0)
    make_question(lesson, "Belgilar haqida", order=1)
    auth(api, student)
    rows = api.get("/api/v1/questions/?search=svetofor").json()["results"]
    assert [r["text"] for r in rows] == ["Svetofor haqida"]


def test_search_matches_russian_column(api, student, auth, lesson):
    from apps.content.models import Question

    Question.objects.create(lesson=lesson, text_uz="Uz matn",
                            text_ru="Светофор", is_published=True)
    auth(api, student)
    rows = api.get("/api/v1/questions/?search=Светофор").json()["results"]
    assert len(rows) == 1


def test_search_matches_cyrillic_column(api, student, auth, lesson):
    from apps.content.models import Question

    Question.objects.create(lesson=lesson, text_uz="Uz matn",
                            text_cry="Светофор ҳақида", is_published=True)
    auth(api, student)
    assert len(api.get("/api/v1/questions/?search=ҳақида").json()["results"]) == 1


def test_results_are_paginated(api, student, auth, lesson, make_question):
    for index in range(25):
        make_question(lesson, f"Savol {index}", order=index)
    auth(api, student)
    body = api.get("/api/v1/questions/").json()
    assert body["count"] == 25
    assert len(body["results"]) == 20


def test_hides_correct_answer_by_default(api, student, auth, question):
    auth(api, student)
    row = api.get("/api/v1/questions/").json()["results"][0]
    assert "is_true" not in row["answers"][0]


def test_study_mode_shows_correct_answer(api, student, auth, question):
    auth(api, student)
    row = api.get("/api/v1/questions/?mode=study").json()["results"][0]
    assert "is_true" in row["answers"][0]


# Review Focus #1 — qidiruv yo'li
def test_unpublished_hidden_from_question_list(api, student, auth, lesson, make_question):
    make_question(lesson, "Ko'rinadigan", order=0)
    make_question(lesson, "Yashirin qidiruv savoli", order=1, published=False)
    auth(api, student)
    texts = [r["text"] for r in api.get("/api/v1/questions/").json()["results"]]
    assert "Yashirin qidiruv savoli" not in texts
    assert "Ko'rinadigan" in texts


def test_teacher_sees_unpublished_in_question_list(api, teacher, auth, lesson,
                                                   make_question):
    make_question(lesson, "Yashirin qidiruv savoli", order=1, published=False)
    auth(api, teacher)
    texts = [r["text"] for r in api.get("/api/v1/questions/").json()["results"]]
    assert "Yashirin qidiruv savoli" in texts
