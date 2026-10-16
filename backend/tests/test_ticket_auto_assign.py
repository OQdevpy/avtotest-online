"""Yangi savol avtomatik biletga tushadi.

Biletlar barcha savollarni 20 tadan bo'lib chiqadi (eski seoul `question.json`:
56 × 20 + oxirgisi 16). Yangi savol to'lmagan eng kichik raqamli biletga
qo'shiladi; hammasi to'la bo'lsa keyingi raqamli yangi bilet ochiladi.
"""

import pytest

from apps.content.models import Question, Ticket, TicketQuestion
from apps.content.tickets import TICKET_SIZE, assign_to_ticket


def _fill(ticket, lesson, make_question, count):
    for i in range(count):
        q = make_question(lesson, f"T{ticket.number}-{i}")
        TicketQuestion.objects.create(ticket=ticket, question=q, order=i + 1)


def _create_via_api(api, admin_user, auth, lesson):
    auth(api, admin_user)
    response = api.post("/api/v1/manage/questions/",
                        {"lesson": lesson.id, "text_uz": "Yangi savol", "order": 99},
                        format="json")
    assert response.status_code == 201, response.json()
    return Question.objects.get(pk=response.json()["id"])


def test_new_question_fills_last_partial_ticket(api, admin_user, auth, lesson, make_question):
    full = Ticket.objects.create(number=1)
    _fill(full, lesson, make_question, TICKET_SIZE)
    partial = Ticket.objects.create(number=2)
    _fill(partial, lesson, make_question, 16)

    question = _create_via_api(api, admin_user, auth, lesson)

    item = TicketQuestion.objects.get(question=question)
    assert item.ticket == partial
    assert item.order == 17
    assert Ticket.objects.count() == 2


def test_new_ticket_opened_when_all_full(api, admin_user, auth, lesson, make_question):
    for number in (1, 2):
        _fill(Ticket.objects.create(number=number), lesson, make_question, TICKET_SIZE)

    question = _create_via_api(api, admin_user, auth, lesson)

    item = TicketQuestion.objects.get(question=question)
    assert item.ticket.number == 3
    assert item.order == 1


def test_first_ticket_created_when_none_exist(api, admin_user, auth, lesson):
    question = _create_via_api(api, admin_user, auth, lesson)
    assert TicketQuestion.objects.get(question=question).ticket.number == 1


def test_gap_left_by_deleted_question_is_filled_first(api, admin_user, auth, lesson,
                                                      make_question):
    first = Ticket.objects.create(number=1)
    _fill(first, lesson, make_question, TICKET_SIZE)
    second = Ticket.objects.create(number=2)
    _fill(second, lesson, make_question, 10)
    first.items.order_by("order").first().question.delete()  # 1-biletda bo'shliq

    question = _create_via_api(api, admin_user, auth, lesson)

    item = TicketQuestion.objects.get(question=question)
    assert item.ticket == first
    assert first.items.count() == TICKET_SIZE


def test_assign_is_idempotent(lesson, make_question):
    question = make_question(lesson, "Bir marta")
    assign_to_ticket(question)
    assign_to_ticket(question)
    assert TicketQuestion.objects.filter(question=question).count() == 1


def test_plain_orm_create_does_not_assign(lesson, make_question):
    """Import buyruqlari ORM orqali yaratadi — ular biletni o'zi boshqaradi."""
    question = make_question(lesson, "Import")
    assert not TicketQuestion.objects.filter(question=question).exists()


@pytest.mark.django_db
def test_django_admin_add_assigns_ticket(client, django_user_model, lesson):
    superuser = django_user_model.objects.create_superuser("+998901119999", "Parol1234!")
    client.force_login(superuser)
    response = client.post("/admin/content/question/add/", {
        "lesson": lesson.id, "text_uz": "Admin savoli", "text_ru": "", "text_cry": "",
        "order": 0, "is_published": "on",
        "answers-TOTAL_FORMS": "0", "answers-INITIAL_FORMS": "0",
        "answers-MIN_NUM_FORMS": "0", "answers-MAX_NUM_FORMS": "1000",
    })
    assert response.status_code == 302, response.content[:2000]
    question = Question.objects.get(text_uz="Admin savoli")
    assert TicketQuestion.objects.filter(question=question).exists()


def test_command_assigns_unticketed_questions_in_section_lesson_order(section, make_question):
    """`assign_tickets` biletsiz savollarni bo'lim → dars → tartib bo'yicha joylaydi."""
    from io import StringIO

    from django.core.management import call_command

    from apps.content.models import Lesson, Section

    later_section = Section.objects.create(name_uz="2-bo'lim", order=2)
    l_late = Lesson.objects.create(section=later_section, name_uz="B", order=1)
    l_second = Lesson.objects.create(section=section, name_uz="A2", order=2)
    l_first = Lesson.objects.create(section=section, name_uz="A1", order=1)

    ticket = Ticket.objects.create(number=1)
    _fill(ticket, l_first, make_question, TICKET_SIZE - 2)  # 2 ta joy bor

    q_late = make_question(l_late, "late", order=1)
    q_second = make_question(l_second, "second", order=1)
    q_first_b = make_question(l_first, "first-b", order=2)
    q_first_a = make_question(l_first, "first-a", order=1)
    hidden = make_question(l_first, "hidden", order=0, published=False)

    out = StringIO()
    call_command("assign_tickets", "--dry-run", stdout=out)
    assert "4" in out.getvalue()
    assert TicketQuestion.objects.count() == TICKET_SIZE - 2  # dry-run hech narsa yozmaydi

    call_command("assign_tickets", stdout=StringIO())

    def where(q):
        item = TicketQuestion.objects.get(question=q)
        return item.ticket.number, item.order

    assert where(q_first_a) == (1, TICKET_SIZE - 1)
    assert where(q_first_b) == (1, TICKET_SIZE)
    assert where(q_second) == (2, 1)
    assert where(q_late) == (2, 2)
    assert not TicketQuestion.objects.filter(question=hidden).exists()

    call_command("assign_tickets", stdout=StringIO())  # ikkinchi marta — o'zgarishsiz
    assert TicketQuestion.objects.count() == TICKET_SIZE + 2
