"""Kontent versiyasi — desktop yangi/o'zgargan savollarni shu bilan sezadi.

Versiya o'quvchiga ko'rinadigan hamma narsadan hisoblanadi: bo'lim, mavzu,
savol, javob, bilet va blits (nomi, tartibi, qayerga tegishliligi). Tartiblash
va ko'chirish `queryset.update()` bilan yoziladi — `updated_at` yangilanmaydi,
shuning uchun vaqtga emas, qiymatlarning o'ziga xesh olinadi. O'chirish ham
sezildi: qator yo'qoladi. ~10 ming qisqa qator, bir necha millisekund.
"""

import hashlib

from django.db.models import Max

from .models import Answer, Blits, BlitsQuestion, Lesson, Question, Section, Ticket, TicketQuestion

NAMES = ("name_uz", "name_ru", "name_cry")

PARTS = (
    (Section, ("id", "order", *NAMES)),
    (Lesson, ("id", "section_id", "order", *NAMES)),
    (Question, ("id", "lesson_id", "order", "is_published", "updated_at")),
    (Answer, ("id", "question_id", "order", "is_true", "updated_at")),
    (Ticket, ("id", "number", "is_pro")),
    (TicketQuestion, ("ticket_id", "question_id", "order")),
    (Blits, ("id", "order", "is_active", *NAMES)),
    (BlitsQuestion, ("blits_id", "question_id", "order")),
)


def content_version() -> str:
    digest = hashlib.sha1()
    for model, fields in PARTS:
        digest.update(model.__name__.encode())
        # To'liq tartib: bir xil ma'lumot har doim bir xil xesh bersin.
        for row in model.objects.order_by(*fields).values_list(*fields).iterator():
            digest.update(repr(row).encode())
    return digest.hexdigest()


def content_updated_at():
    """Savol yoki javob oxirgi marta qo'shilgan/tahrirlangan vaqt (bosh sahifadagi sana)."""
    stamps = [
        Question.objects.aggregate(t=Max("updated_at"))["t"],
        Answer.objects.aggregate(t=Max("updated_at"))["t"],
    ]
    stamps = [t for t in stamps if t is not None]
    return max(stamps) if stamps else None
