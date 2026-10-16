"""Yangi savolni biletga avtomatik joylash.

Biletlar barcha savollarni 20 tadan bo'lib chiqadi (eski seoul `question.json`:
56 × 20 + oxirgisi 16). Mavjud biletlar tarkibi o'zgartirilmaydi — o'quvchi
natijalari (`TicketResult`) shu tarkibga bog'langan. Yangi savol to'lmagan eng
kichik raqamli biletga tushadi (o'chirilgan savol qoldirgan bo'shliq ham shunday
to'ladi); hammasi to'la bo'lsa keyingi raqamli bilet ochiladi.

Faqat shef yaratgan savol uchun chaqiriladi (`manage/questions/` va Django
admin). Import buyruqlari biletlarni o'zi tuzadi, shuning uchun signal emas.
"""

from django.db import IntegrityError, transaction
from django.db.models import Count, Max

from .models import Question, Ticket, TicketQuestion

TICKET_SIZE = 20


def assign_to_ticket(question: Question) -> Ticket:
    """Savolni biletga qo'shadi va o'sha biletni qaytaradi (takroriy chaqiruv xavfsiz)."""
    existing = TicketQuestion.objects.filter(question=question).select_related("ticket").first()
    if existing is not None:
        return existing.ticket

    # Ikki shef bir vaqtda yangi bilet ochsa, `number` unique — biri qayta urinadi.
    for _ in range(3):
        try:
            with transaction.atomic():
                return _place(question)
        except IntegrityError:
            continue
    raise RuntimeError(f"Savol {question.pk} biletga joylanmadi")


def _place(question: Question) -> Ticket:
    candidates = (
        Ticket.objects.annotate(size=Count("items"))
        .filter(size__lt=TICKET_SIZE)
        .order_by("number")
        .values_list("pk", flat=True)
    )
    for pk in candidates:
        ticket = Ticket.objects.select_for_update().get(pk=pk)
        # Qulfdan keyin qayta sanaymiz — orada boshqa savol tushgan bo'lishi mumkin.
        if ticket.items.count() < TICKET_SIZE:
            return _append(ticket, question)

    last = Ticket.objects.aggregate(n=Max("number"))["n"] or 0
    return _append(Ticket.objects.create(number=last + 1), question)


def _append(ticket: Ticket, question: Question) -> Ticket:
    order = (ticket.items.aggregate(n=Max("order"))["n"] or 0) + 1
    TicketQuestion.objects.create(ticket=ticket, question=question, order=order)
    return ticket
