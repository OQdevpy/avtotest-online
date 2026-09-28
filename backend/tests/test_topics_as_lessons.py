"""`Mavzular` = `Darslar` — Topic modeli o'chirilgan, /topics/ Lesson'dan uzatiladi.

Sabab: shef "Mavzular" bo'limini ochsa, u har doim bo'sh bo'lardi — Topic
jadvali hech qaysi import buyrug'i tomonidan to'ldirilmagan. Mobil ilova
`/topics/` ni chaqiradi, shuning uchun yo'l saqlanadi, lekin endi Lesson
ma'lumotidan uzatiladi.
"""

import pytest

pytestmark = pytest.mark.django_db


def test_topics_list_mirrors_lessons(api, student, auth, lesson, question):
    auth(api, student)
    topics = api.get("/api/v1/topics/").json()
    lessons = api.get("/api/v1/lessons/").json()
    assert [t["id"] for t in topics] == [l["id"] for l in lessons]
    assert topics[0]["name"] == lessons[0]["name"]
    assert topics[0]["order"] == lessons[0]["order"]
    assert topics[0]["question_count"] == lessons[0]["question_count"]


def test_topic_detail_mirrors_lesson_detail(api, student, auth, question):
    auth(api, student)
    topic = api.get(f"/api/v1/topics/{question.lesson_id}/").json()
    lesson = api.get(f"/api/v1/lessons/{question.lesson_id}/").json()
    assert [q["id"] for q in topic["questions"]] == [q["id"] for q in lesson["questions"]]
    # Dars ekrani — o'rganish rejimi, kalit ochiq (Task 6/Final review qarori).
    assert "is_true" in topic["questions"][0]["answers"][0]


def test_topic_detail_hides_unpublished(api, student, auth, lesson, make_question):
    make_question(lesson, "Yashirin mavzu savoli", order=9, published=False)
    auth(api, student)
    body = api.get(f"/api/v1/topics/{lesson.id}/").json()
    assert "Yashirin mavzu savoli" not in [q["text"] for q in body["questions"]]


def test_topics_requires_auth(api):
    assert api.get("/api/v1/topics/").status_code == 401


def test_topic_model_removed():
    from apps.content import models

    assert not hasattr(models, "Topic")


def test_topic_not_registered_in_admin():
    from django.apps import apps as dj_apps
    from django.contrib import admin

    for model in dj_apps.get_models():
        assert model.__name__ != "Topic"
    assert all(m.__name__ != "Topic" for m in admin.site._registry)
