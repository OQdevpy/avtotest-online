"""Telegram kontakti bo'yicha foydalanuvchini topish yoki yaratish.

Kirish va ro'yxatdan o'tish bitta oqim: raqam bazada bo'lsa o'sha hisob,
bo'lmasa yangi o'quvchi (mehmon bo'lsa — o'sha mehmon hisobi aylanadi).
"""

from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Device, User
from apps.accounts.serializers import guest_from_refresh
from apps.billing.models import Student

from .models import TelegramAccount

# Yangi hisobga beriladigan PRO sovg'a (avvalgi ro'yxatdan o'tish qoidasi).
WELCOME_PRO_DAYS = 12


def is_blocked(user: User) -> bool:
    """Hisob yoki avtomaktab tomonidan bloklangan."""
    return not user.is_active or Student.objects.filter(user=user, is_active=False).exists()


@transaction.atomic
def user_for_phone(phone: str, full_name: str, lang: str,
                   guest_refresh: str = "") -> tuple[User, bool]:
    """`(user, created)`. Mavjud hisobga mehmon ma'lumoti ko'chirilmaydi."""
    guest = guest_from_refresh(guest_refresh)
    existing = (User.objects.select_for_update()
                .filter(phone=phone).exclude(role=User.Role.GUEST).first())
    if existing is not None:
        if guest is not None:
            # Mehmon mavjud hisobga kirdi — mehmon sessiyasi tashlab ketiladi.
            Device.objects.filter(user=guest, is_active=True).update(is_active=False)
        return existing, False

    if guest is not None:
        # Yangi hisob ochilmaydi: natijalar, xatolar, sevimlilar shu userda qoladi.
        user = guest
        user.phone = phone
        user.role = User.Role.STUDENT
        Device.objects.filter(user=user, is_active=True).update(is_active=False)
    else:
        user = User(phone=phone, role=User.Role.STUDENT, language=lang)
    user.full_name = full_name[:120]
    user.set_unusable_password()
    user.is_pro = True
    user.pro_until = timezone.now() + timedelta(days=WELCOME_PRO_DAYS)
    user.save()
    TelegramAccount.objects.filter(phone=phone, user__isnull=True).update(user=user)
    return user, True
