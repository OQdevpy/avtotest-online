"""Profil rangi uchun PRO darajasi: 1 — 15 kun, 2 — 1 oy, 3 — 3 oy; PRO'siz — null."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.payments.models import ProOrder, ProPlan

pytestmark = pytest.mark.django_db
ME = "/api/v1/auth/me/"


def tier(api, auth, user):
    auth(api, user)
    return api.get(ME).json()["pro_tier"]


def make_pro(user, days):
    user.is_pro, user.pro_until = True, timezone.now() + timedelta(days=days)
    user.save()


def paid(user, days):
    plan = ProPlan.objects.create(title_uz=f"{days} kun", days=days, price=1000)
    return ProOrder.objects.create(user=user, plan=plan, title=plan.title_uz, days=days,
                                   amount=1000, provider="payme", status="paid",
                                   paid_at=timezone.now())


def test_no_pro_is_null(api, auth, student):
    assert tier(api, auth, student) is None


@pytest.mark.parametrize("plan_days,expected", [(15, 1), (30, 2), (90, 3)])
def test_tier_from_paid_plan(api, auth, student, plan_days, expected):
    paid(student, plan_days)
    make_pro(student, 5)  # qolgan kun kam bo'lsa ham daraja tarifdan
    assert tier(api, auth, student) == expected


def test_latest_paid_order_wins(api, auth, student):
    paid(student, 90)
    paid(student, 15)
    make_pro(student, 100)
    assert tier(api, auth, student) == 1


def test_expired_pro_is_null_even_with_order(api, auth, student):
    paid(student, 90)
    student.is_pro, student.pro_until = True, timezone.now() - timedelta(days=1)
    student.save()
    assert tier(api, auth, student) is None


@pytest.mark.parametrize("left,expected", [(10, 1), (25, 2), (200, 3)])
def test_admin_granted_by_days_left(api, auth, student, left, expected):
    make_pro(student, left)
    assert tier(api, auth, student) == expected


def test_forever_pro_is_top(api, auth, student):
    student.is_pro, student.pro_until = True, None
    student.save()
    assert tier(api, auth, student) == 3
