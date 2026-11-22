"""0012/0013: yashirin savollar nashr etiladi, har savol bitta biletda."""

import pytest
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor

pytestmark = pytest.mark.django_db(transaction=True)

BEFORE = [("content", "0011_lesson_banner")]
AFTER = [("content", "0013_ticketquestion_one_ticket")]


def migrate(targets):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(targets)
    return executor.loader.project_state(targets).apps


def test_migration_publishes_dedupes_and_assigns():
    old = migrate(BEFORE)
    Section = old.get_model("content", "Section")
    Lesson = old.get_model("content", "Lesson")
    Question = old.get_model("content", "Question")
    Ticket = old.get_model("content", "Ticket")
    TicketQuestion = old.get_model("content", "TicketQuestion")

    lesson = Lesson.objects.create(section=Section.objects.create(name_uz="B", order=1),
                                   name_uz="D", order=1)
    q = [Question.objects.create(lesson=lesson, text_uz=f"S{i}", order=i, is_published=True)
         for i in range(23)]
    hidden = Question.objects.create(lesson=lesson, text_uz="API", order=50, is_published=False)
    t1, t2 = Ticket.objects.create(number=1), Ticket.objects.create(number=2)
    for i in range(20):
        TicketQuestion.objects.create(ticket=t1, question=q[i], order=i + 1)
    TicketQuestion.objects.create(ticket=t2, question=q[20], order=1)
    TicketQuestion.objects.create(ticket=t2, question=q[0], order=2)  # takror

    new = migrate(AFTER)
    Question = new.get_model("content", "Question")
    TicketQuestion = new.get_model("content", "TicketQuestion")

    assert Question.objects.filter(is_published=False).count() == 0
    assert list(TicketQuestion.objects.filter(question_id=q[0].pk)
                .values_list("ticket__number", flat=True)) == [1]
    t2_items = list(TicketQuestion.objects.filter(ticket__number=2)
                    .order_by("order").values_list("question_id", "order"))
    # q21, q22 va yashirin savol ikkinchi biletga, tartib bilan
    assert t2_items == [(q[20].pk, 1), (q[21].pk, 2), (q[22].pk, 3), (hidden.pk, 4)]
    assert TicketQuestion.objects.values("question_id").distinct().count() == 24

    with pytest.raises(IntegrityError), transaction.atomic():
        TicketQuestion.objects.create(ticket_id=t1.pk, question_id=q[21].pk, order=99)
