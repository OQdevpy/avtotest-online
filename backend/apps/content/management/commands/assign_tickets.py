"""Hech bir biletda yo'q nashr etilgan savollarni biletlarga joylaydi.

Manba — baza (JSON emas). Savollar bo'lim → dars → savol tartibi bo'yicha
olinadi va `assign_to_ticket` qoidasi bilan joylanadi: avval to'lmagan biletlar
(eng kichik raqamdan), so'ng yangi biletlar. Mavjud bilet tarkibi o'zgarmaydi.

    python manage.py assign_tickets --dry-run
    python manage.py assign_tickets
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.content.models import Question, Ticket
from apps.content.tickets import assign_to_ticket


class Command(BaseCommand):
    help = "Biletsiz savollarni bo'lim → dars → tartib bo'yicha biletlarga joylaydi"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Faqat nechta savol joylanishini ko'rsatadi")

    def handle(self, *args, dry_run=False, **options):
        pending = (
            Question.published.filter(tickets__isnull=True)
            .select_related("lesson__section")
            .order_by("lesson__section__order", "lesson__section_id",
                      "lesson__order", "lesson_id", "order", "id")
        )
        count = pending.count()
        if dry_run:
            self.stdout.write(f"Biletsiz nashr etilgan savollar: {count} ta (dry-run, o'zgarish yo'q)")
            return

        before = Ticket.objects.count()
        with transaction.atomic():
            for question in pending:
                assign_to_ticket(question)
        created = Ticket.objects.count() - before
        self.stdout.write(self.style.SUCCESS(
            f"{count} ta savol joylandi, {created} ta yangi bilet ochildi."
        ))
