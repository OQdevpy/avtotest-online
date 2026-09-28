import pytest

pytestmark = pytest.mark.django_db


# --- Ruxsat -----------------------------------------------------------------

def test_student_cannot_list_manage_questions(api, student, auth):
    auth(api, student)
    assert api.get("/api/v1/manage/questions/").status_code == 403


def test_teacher_cannot_create_question(api, teacher, auth, lesson):
    auth(api, teacher)
    response = api.post("/api/v1/manage/questions/",
                        {"lesson": lesson.id, "text_uz": "Savol"}, format="json")
    assert response.status_code == 403


def test_anonymous_cannot_list_manage_questions(api):
    assert api.get("/api/v1/manage/questions/").status_code == 401


def test_admin_can_list_manage_questions(api, admin_user, auth, question):
    auth(api, admin_user)
    assert api.get("/api/v1/manage/questions/").status_code == 200


# --- Yaratish va tahrirlash -------------------------------------------------

def test_admin_creates_question_unpublished_by_default(api, admin_user, auth, lesson):
    auth(api, admin_user)
    response = api.post("/api/v1/manage/questions/",
                        {"lesson": lesson.id, "text_uz": "Yangi savol",
                         "text_ru": "", "text_cry": ""}, format="json")
    assert response.status_code == 201
    assert response.json()["is_published"] is False


def test_admin_can_publish_question(api, admin_user, auth, question):
    auth(api, admin_user)
    response = api.patch(f"/api/v1/manage/questions/{question.id}/",
                         {"is_published": True}, format="json")
    assert response.status_code == 200
    question.refresh_from_db()
    assert question.is_published


def test_manage_serializer_exposes_all_three_languages(api, admin_user, auth, question):
    auth(api, admin_user)
    body = api.get(f"/api/v1/manage/questions/{question.id}/").json()
    assert {"text_uz", "text_ru", "text_cry"} <= set(body)
    # `manage/` da til yig'ilmaydi — bitta `text` maydoni bo'lmasligi kerak.
    assert "text" not in body


def test_manage_question_includes_answers(api, admin_user, auth, question):
    auth(api, admin_user)
    body = api.get(f"/api/v1/manage/questions/{question.id}/").json()
    assert len(body["answers"]) == 2
    assert body["answers"][0]["is_true"] is True


def test_admin_sees_unpublished_questions_in_manage(api, admin_user, auth, lesson,
                                                   make_question):
    make_question(lesson, "Yashirin", order=1, published=False)
    auth(api, admin_user)
    texts = [r["text_uz"] for r in api.get("/api/v1/manage/questions/").json()["results"]]
    assert "Yashirin" in texts


def test_admin_deletes_question(api, admin_user, auth, question):
    from apps.content.models import Question

    auth(api, admin_user)
    assert api.delete(f"/api/v1/manage/questions/{question.id}/").status_code == 204
    assert not Question.objects.filter(pk=question.pk).exists()


def test_admin_creates_answer(api, admin_user, auth, question):
    auth(api, admin_user)
    response = api.post("/api/v1/manage/answers/",
                        {"question": question.id, "text_uz": "Yangi javob",
                         "is_true": False, "order": 2}, format="json")
    assert response.status_code == 201


def test_admin_creates_section_and_lesson(api, admin_user, auth):
    auth(api, admin_user)
    section = api.post("/api/v1/manage/sections/",
                       {"name_uz": "Yangi bo'lim", "order": 9}, format="json")
    assert section.status_code == 201
    lesson = api.post("/api/v1/manage/lessons/",
                      {"section": section.json()["id"], "name_uz": "Yangi dars",
                       "order": 1}, format="json")
    assert lesson.status_code == 201


def test_admin_creates_blits(api, admin_user, auth):
    auth(api, admin_user)
    assert api.post("/api/v1/manage/blits/",
                    {"name_uz": "Blits 9", "order": 9}, format="json").status_code == 201


def test_admin_creates_ticket(api, admin_user, auth):
    auth(api, admin_user)
    assert api.post("/api/v1/manage/tickets/",
                    {"number": 99}, format="json").status_code == 201


# --- Tartiblash -------------------------------------------------------------

def test_reorder_sets_order_by_position(api, admin_user, auth, section):
    from apps.content.models import Lesson

    first = Lesson.objects.create(section=section, name_uz="A", order=0)
    second = Lesson.objects.create(section=section, name_uz="B", order=1)
    third = Lesson.objects.create(section=section, name_uz="C", order=2)
    auth(api, admin_user)
    response = api.post("/api/v1/manage/lessons/reorder/",
                        {"ids": [third.id, first.id, second.id]}, format="json")
    assert response.status_code == 200
    assert [l.id for l in Lesson.objects.order_by("order")] == [third.id, first.id, second.id]


def test_reorder_rejects_unknown_id(api, admin_user, auth, lesson):
    from apps.content.models import Lesson

    auth(api, admin_user)
    response = api.post("/api/v1/manage/lessons/reorder/",
                        {"ids": [lesson.id, 999999]}, format="json")
    assert response.status_code == 400
    # Hech narsa yozilmagan bo'lishi kerak.
    assert Lesson.objects.get(pk=lesson.pk).order == 1


def test_reorder_rejects_empty_list(api, admin_user, auth):
    auth(api, admin_user)
    assert api.post("/api/v1/manage/lessons/reorder/",
                    {"ids": []}, format="json").status_code == 400


def test_reorder_questions(api, admin_user, auth, lesson, make_question):
    from apps.content.models import Question

    a = make_question(lesson, "A", order=0)
    b = make_question(lesson, "B", order=1)
    auth(api, admin_user)
    api.post("/api/v1/manage/questions/reorder/", {"ids": [b.id, a.id]}, format="json")
    assert [q.id for q in Question.objects.order_by("order")] == [b.id, a.id]


def test_student_cannot_reorder(api, student, auth, lesson):
    auth(api, student)
    assert api.post("/api/v1/manage/lessons/reorder/",
                    {"ids": [lesson.id]}, format="json").status_code == 403


# --- Blits ichidagi savollar (manage/blits-questions/) ----------------------
# admin-panel's blits sahifasi savolni blitsga qo'shadi, o'chiradi va
# tartiblaydi — `ManageBlitsSerializer.items` faqat o'qish uchun bo'lgani
# sabab bu yozish yo'li alohida kerak edi.

def test_admin_adds_question_to_blits(api, admin_user, auth, blits, lesson, make_question):
    from apps.content.models import BlitsQuestion

    extra = make_question(lesson, "Yangi blits savoli", order=9)
    auth(api, admin_user)
    response = api.post("/api/v1/manage/blits-questions/",
                        {"blits": blits.id, "question": extra.id, "order": 3},
                        format="json")
    assert response.status_code == 201
    assert BlitsQuestion.objects.filter(blits=blits, question=extra).exists()


def test_admin_removes_question_from_blits(api, admin_user, auth, blits):
    from apps.content.models import BlitsQuestion, Question

    link = blits.items.first()
    question_id = link.question_id
    auth(api, admin_user)
    assert api.delete(f"/api/v1/manage/blits-questions/{link.id}/").status_code == 204
    assert not BlitsQuestion.objects.filter(pk=link.pk).exists()
    # Savolning o'zi o'chmaydi — faqat blitsdagi bog'lanish.
    assert Question.objects.filter(pk=question_id).exists()


def test_admin_lists_blits_questions_filtered_by_blits(api, admin_user, auth, blits):
    auth(api, admin_user)
    response = api.get(f"/api/v1/manage/blits-questions/?blits={blits.id}")
    assert response.status_code == 200
    assert len(response.json()["results"]) == 3


def test_admin_reorders_questions_within_blits(api, admin_user, auth, blits):
    from apps.content.models import BlitsQuestion

    ids = list(blits.items.order_by("order").values_list("id", flat=True))
    auth(api, admin_user)
    response = api.post("/api/v1/manage/blits-questions/reorder/",
                        {"ids": [ids[2], ids[0], ids[1]]}, format="json")
    assert response.status_code == 200
    assert list(BlitsQuestion.objects.order_by("order").values_list("id", flat=True)) == [
        ids[2], ids[0], ids[1],
    ]


def test_student_cannot_add_question_to_blits(api, student, auth, blits, question):
    auth(api, student)
    response = api.post("/api/v1/manage/blits-questions/",
                        {"blits": blits.id, "question": question.id, "order": 0},
                        format="json")
    assert response.status_code == 403
