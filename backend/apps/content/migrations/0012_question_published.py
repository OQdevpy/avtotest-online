"""Yangi savol darhol o'quvchiga ko'rinsin va har savol bitta biletda bo'lsin.

1. `is_published` endi standart bo'yicha True (bazada ham — `db_default`).
   Avval API orqali maydonsiz kiritilgan savollar yashirin qolib ketgan edi,
   ular nashr etiladi.
2. Bir savol bir nechta biletda bo'lsa — eng kichik raqamli biletda qoladi.
3. Hech bir biletda yo'q savollar `assign_to_ticket` qoidasi bilan joylanadi:
   to'lmagan eng kichik raqamli bilet, hammasi to'la bo'lsa yangi bilet.
4. Bazadagi cheklov (savol faqat bitta biletda) — 0013 da, alohida
   tranzaksiyada (Postgres ma'lumot yozilgan jadvalni shu tranzaksiyada
   ALTER qila olmaydi).
"""

from django.db import migrations, models
from django.db.models import Count, Max

TICKET_SIZE = 20


def fix_existing(apps, schema_editor):
    Question = apps.get_model("content", "Question")
    Ticket = apps.get_model("content", "Ticket")
    TicketQuestion = apps.get_model("content", "TicketQuestion")

    Question.objects.filter(is_published=False).update(is_published=True)

    seen, duplicates = set(), []
    rows = TicketQuestion.objects.order_by("question_id", "ticket__number", "order", "id")
    for pk, question_id in rows.values_list("pk", "question_id"):
        if question_id in seen:
            duplicates.append(pk)
        else:
            seen.add(question_id)
    TicketQuestion.objects.filter(pk__in=duplicates).delete()

    pending = (
        Question.objects.exclude(pk__in=TicketQuestion.objects.values("question_id"))
        .order_by("lesson__section__order", "lesson__section_id",
                  "lesson__order", "lesson_id", "order", "id")
        .values_list("pk", flat=True)
    )
    tickets = list(
        Ticket.objects.annotate(size=Count("items"), last=Max("items__order"))
        .order_by("number")
        .values_list("pk", "number", "size", "last")
    )
    state = [[pk, number, size, last or 0] for pk, number, size, last in tickets]
    for question_id in pending:
        slot = next((t for t in state if t[2] < TICKET_SIZE), None)
        if slot is None:
            number = (state[-1][1] if state else 0) + 1
            slot = [Ticket.objects.create(number=number).pk, number, 0, 0]
            state.append(slot)
        slot[3] += 1
        slot[2] += 1
        TicketQuestion.objects.create(ticket_id=slot[0], question_id=question_id, order=slot[3])


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0011_lesson_banner"),
    ]

    operations = [
        migrations.AlterField(
            model_name="question",
            name="is_published",
            field=models.BooleanField(
                db_default=True,
                db_index=True,
                default=True,
                verbose_name="Nashr etilgan",
            ),
        ),
        migrations.RunPython(fix_existing, migrations.RunPython.noop),
    ]
