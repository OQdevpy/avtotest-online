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

from . import legacy
from .models import TelegramAccount



def welcome_pro_days() -> int:
    """Yangi hisobga beriladigan bepul PRO kunlari — admin'dagi «Ilova sozlamalari»dan."""
    from apps.releases.models import AppSettings

    return AppSettings.current().welcome_pro_days


def is_blocked(user: User) -> bool:
    """Hisob yoki avtomaktab tomonidan bloklangan."""
    return not user.is_active or Student.objects.filter(user=user, is_active=False).exists()


@transaction.atomic
def user_for_phone(phone: str, full_name: str, lang: str,
                   guest_refresh: str = "") -> tuple[User, bool]:
    """`(user, created)`. Mavjud hisobga mehmon ma'lumoti ko'chirilmaydi.

    Raqam bu bazada yo'q, lekin eski avtotest bazasida bo'lsa — o'sha hisob
    ma'lumoti bilan ochiladi (`legacy`)."""
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
    days = welcome_pro_days()
    if days:
        user.is_pro = True
        user.pro_until = timezone.now() + timedelta(days=days)
    else:
        # Sovg'a yo'q — mehmon sinovidagi PRO ham davom etmaydi
        user.is_pro = False
        user.pro_until = None

    # Eski avtotest ilovasidagi hisob — ism, til, PRO muddati ko'chiriladi.
    old = legacy.legacy_user(phone)
    if old is not None:
        user.full_name = (old["full_name"] or full_name)[:120]
        user.language = old["language"]
        user.is_active = old["is_active"]
        if old["date_joined"]:
            user.date_joined = min(user.date_joined, old["date_joined"])
        if legacy.pro_active(old) and (
            not user.is_pro or old["pro_until"] is None or old["pro_until"] > user.pro_until
        ):
            user.is_pro = True
            user.pro_until = old["pro_until"]
    user.save()
    TelegramAccount.objects.filter(phone=phone, user__isnull=True).update(user=user)
    return user, True
