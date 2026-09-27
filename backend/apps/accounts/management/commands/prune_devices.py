"""Muddati o'tgan qurilma sessiyalarini o'chiradi. Idempotent."""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import Device


class Command(BaseCommand):
    help = "Muddati o'tgan qurilmalarni is_active=False qiladi"

    def handle(self, *args, **options):
        count = Device.objects.filter(
            is_active=True, expires_at__isnull=False, expires_at__lte=timezone.now()
        ).update(is_active=False)
        self.stdout.write(f"{count} ta qurilma o'chirildi")
