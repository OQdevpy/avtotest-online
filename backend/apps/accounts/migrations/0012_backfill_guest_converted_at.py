"""Avval mehmondan o'tganlarni belgilash.

Mobil sessiyalar muddatsiz (`expires_at` bo'sh) — muddatli mobil sessiya faqat
mehmonda bo'ladi. Shunday sessiyasi bor, hozir mehmon bo'lmagan hisob mehmondan
o'tgan. Vaqti: Telegram tasdiqlangan payt, bo'lmasa mehmon sessiyasi tugagan payt.
"""

from django.db import migrations
from django.db.models import Min


def backfill(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Device = apps.get_model("accounts", "Device")
    TelegramAccount = apps.get_model("telegramauth", "TelegramAccount")

    guest_sessions = (Device.objects.filter(platform="mobile", expires_at__isnull=False)
                      .exclude(user__role="guest")
                      .values("user_id").annotate(first=Min("created_at")))
    verified = dict(TelegramAccount.objects.filter(user__isnull=False, verified_at__isnull=False)
                    .values_list("user_id").annotate(t=Min("verified_at")))
    for row in guest_sessions:
        when = verified.get(row["user_id"]) or row["first"]
        User.objects.filter(pk=row["user_id"], guest_converted_at__isnull=True).update(guest_converted_at=when)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0011_user_guest_converted_at"),
        ("telegramauth", "0001_initial"),
    ]

    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
