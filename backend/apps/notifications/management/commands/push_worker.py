"""Push navbatini yuboradi: `python manage.py push_worker` (compose'da doimiy servis)."""

import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from apps.notifications import push


class Command(BaseCommand):
    help = "Navbatdagi (pending) bildirishnomalarni FCM orqali yuboradi."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Bir marta tekshirib chiqish")
        parser.add_argument("--interval", type=float, default=3.0, help="Tekshirish oralig'i (s)")

    def handle(self, *args, once=False, interval=3.0, **options):
        stuck = push.reset_stuck()
        if stuck:
            self.stdout.write(f"push_worker: {stuck} ta to'xtab qolgan xabar qayta navbatda")
        if not once:
            self.stdout.write("push_worker ishga tushdi"
                              + ("" if push.is_configured() else " (Firebase sozlanmagan!)"))
        while True:
            close_old_connections()
            processed = push.process_pending()
            if once:
                return
            if not processed:
                time.sleep(interval)
