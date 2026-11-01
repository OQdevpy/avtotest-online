"""Muddati o'tgan qurilma sessiyalarini o'chiradi va eski mehmonlarni tozalaydi. Idempotent."""

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import Device, User

# Mehmon muddati tugagach ham shuncha kun saqlanadi — shu orada ro'yxatdan
# o'tsa, natijalari bilan o'quvchiga aylanadi.
GUEST_KEEP_DAYS = 30


class Command(BaseCommand):
    help = "Muddati o'tgan qurilmalarni is_active=False qiladi, eski mehmonlarni o'chiradi"

    def handle(self, *args, **options):
        now = timezone.now()
        count = Device.objects.filter(
            is_active=True, expires_at__isnull=False, expires_at__lte=now
        ).update(is_active=False)
        self.stdout.write(f"{count} ta qurilma o'chirildi")

        cutoff = now - timedelta(days=settings.GUEST_DAYS + GUEST_KEEP_DAYS)
        guests, _ = User.objects.filter(role=User.Role.GUEST, date_joined__lt=cutoff).delete()
        self.stdout.write(f"{guests} ta eski mehmon o'chirildi")
