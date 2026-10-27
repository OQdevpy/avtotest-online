"""`tickets/` va `blits/` ro'yxatidagi `question_ids` — desktop har bir bilet va
blitsni alohida so'ramasligi uchun. Qiymat tafsilot view'idagi savollar bilan
(tartibi va ko'rinishi) bir xil bo'lishi shart."""

import pytest

from apps.content.models import BlitsQuestion, Ticket, TicketQuestion

pytestmark = pytest.mark.django_db


def ids_from_detail(api, path):
    response = api.get(path, {"mode": "study"})
    assert response.status_code == 200
    return [q["id"] for q in response.json()["questions"]]


def by_number(api):
    response = api.get("/api/v1/tickets/", {"page_size": 200})
    assert response.status_code == 200
    return {t["number"]: t for t in response.json()["results"]}


def test_ticket_ids_match_detail_order(api, student, auth, lesson, make_question):
    ticket = Ticket.objects.create(number=1)
    questions = [make_question(lesson, f"S{i}") for i in range(4)]
    # tartib ataylab id tartibidan farqli
    for order, question in zip((3, 1, 4, 2), questions):
        TicketQuestion.objects.create(ticket=ticket, question=question, order=order)
    auth(api, student)

    listed = by_number(api)[1]["question_ids"]
    assert listed == ids_from_detail(api, "/api/v1/tickets/1/")
    assert listed == [questions[1].id, questions[3].id, questions[0].id, questions[2].id]


def test_unpublished_hidden_from_student_but_not_teacher(api, student, teacher, auth,
                                                         lesson, make_question):
    ticket = Ticket.objects.create(number=1)
    shown = make_question(lesson, "Ochiq")
    hidden = make_question(lesson, "Yopiq", published=False)
    TicketQuestion.objects.create(ticket=ticket, question=shown, order=1)
    TicketQuestion.objects.create(ticket=ticket, question=hidden, order=2)

    auth(api, student)
    assert by_number(api)[1]["question_ids"] == [shown.id]
    auth(api, teacher)
    assert by_number(api)[1]["question_ids"] == [shown.id, hidden.id]


def test_pro_ticket_ids_only_for_pro_users(api, student, auth, ticket, question):
    Ticket.objects.filter(pk=ticket.pk).update(is_pro=True)
    auth(api, student)
    assert by_number(api)[1]["question_ids"] is None
    assert api.get("/api/v1/tickets/1/").status_code == 403

    type(student).objects.filter(pk=student.pk).update(is_pro=True)
    assert by_number(api)[1]["question_ids"] == [question.id]


def test_empty_ticket_has_empty_list(api, student, auth, db):
    Ticket.objects.create(number=7)
    auth(api, student)
    assert by_number(api)[7]["question_ids"] == []


def test_blits_ids_match_detail(api, student, auth, blits, lesson, make_question):
    hidden = make_question(lesson, "Yopiq blits", published=False)
    BlitsQuestion.objects.create(blits=blits, question=hidden, order=0)
    auth(api, student)

    response = api.get("/api/v1/blits/")
    assert response.status_code == 200
    listed = response.json()["results"][0]["question_ids"]
    assert hidden.id not in listed
    assert listed == ids_from_detail(api, f"/api/v1/blits/{blits.id}/")
    assert len(listed) == 3


def test_ticket_list_query_count_does_not_grow(api, student, auth, lesson, make_question,
                                               django_assert_max_num_queries):
    for number in range(1, 11):
        ticket = Ticket.objects.create(number=number)
        for i in range(3):
            TicketQuestion.objects.create(ticket=ticket, question=make_question(lesson), order=i)
    auth(api, student)
    with django_assert_max_num_queries(8):
        assert len(by_number(api)) == 10
