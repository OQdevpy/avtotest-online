"""PRO berish/qaytarish va Payme/Click havolalari."""

import base64
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from django.db import transaction
from django.utils import timezone

from apps.payments import links, services
from apps.payments.models import PaymentConfig, ProOrder, ProPlan


@pytest.fixture
def plan(db):
    return ProPlan.objects.create(title_uz="15 kun", days=15, price=15000)


@pytest.fixture
def make_order(plan):
    def _make(user, provider="payme"):
        return ProOrder.objects.create(user=user, plan=plan, title=plan.title_uz,
                                       days=plan.days, amount=plan.price, provider=provider)
    return _make


def grant(order):
    with transaction.atomic():
        return services.grant_pro(order)


def near(a, b):
    return abs((a - b).total_seconds()) < 60


def test_grant_adds_days_from_now(student, make_order):
    order = make_order(student)
    assert grant(order) is True
    student.refresh_from_db()
    order.refresh_from_db()
    assert student.is_pro and student.pro_active
    assert near(student.pro_until, timezone.now() + timedelta(days=15))
    assert order.status == "paid" and order.granted_days == 15 and order.paid_at


def test_grant_extends_active_pro(student, make_order):
    student.is_pro = True
    student.pro_until = timezone.now() + timedelta(days=5)
    student.save()
    grant(make_order(student))
    student.refresh_from_db()
    assert near(student.pro_until, timezone.now() + timedelta(days=20))


def test_grant_after_expired_pro_counts_from_now(student, make_order):
    student.is_pro = True
    student.pro_until = timezone.now() - timedelta(days=30)
    student.save()
    grant(make_order(student))
    student.refresh_from_db()
    assert near(student.pro_until, timezone.now() + timedelta(days=15))


def test_grant_is_idempotent(student, make_order):
    order = make_order(student)
    grant(order)
    student.refresh_from_db()
    first = student.pro_until
    assert grant(order) is False
    student.refresh_from_db()
    assert student.pro_until == first


def test_grant_unlimited_user_untouched(student, make_order):
    student.is_pro = True
    student.pro_until = None
    student.save()
    order = make_order(student)
    grant(order)
    student.refresh_from_db()
    order.refresh_from_db()
    assert student.pro_until is None and student.is_pro
    assert order.granted_days == 0 and order.status == "paid"


def test_revoke_subtracts_and_turns_off(student, make_order):
    order = make_order(student)
    grant(order)
    with transaction.atomic():
        services.revoke_pro(order)
    student.refresh_from_db()
    order.refresh_from_db()
    assert order.status == "refunded" and order.cancelled_at
    assert student.is_pro is False and not student.pro_active


def test_revoke_keeps_remaining_days(student, make_order):
    student.is_pro = True
    student.pro_until = timezone.now() + timedelta(days=30)
    student.save()
    order = make_order(student)
    grant(order)
    with transaction.atomic():
        services.revoke_pro(order)
    student.refresh_from_db()
    assert student.is_pro and near(student.pro_until, timezone.now() + timedelta(days=30))


def test_grant_and_revoke_without_user(student, make_order):
    order = make_order(student)
    order.user = None
    order.save()
    assert grant(order) is True
    with transaction.atomic():
        services.revoke_pro(order)
    order.refresh_from_db()
    assert order.status == "refunded"


def test_cancel_pending(student, make_order):
    order = make_order(student)
    with transaction.atomic():
        services.cancel_pending(order)
    order.refresh_from_db()
    assert order.status == "cancelled" and order.cancelled_at


def test_available_providers_platform(db):
    config = PaymentConfig.get()
    config.click_enabled = True
    config.click_service_id, config.click_merchant_id = "1", "2"
    config.click_secret_key = "c"
    config.save()
    assert services.available_providers(config, "ios") == []
    assert services.available_providers(config, "android") == ["click"]
    config.payme_enabled, config.payme_merchant_id = True, "M"
    config.payme_secret_key = "p"
    config.sell_ios = True
    assert services.available_providers(config, "ios") == ["payme", "click"]
    config.sell_android = False
    assert services.available_providers(config, "android") == []


def _payme_query(url, prefix):
    assert url.startswith(prefix)
    return base64.b64decode(url[len(prefix):]).decode()


def test_payme_url_decodes(student, make_order):
    order = make_order(student)
    config = PaymentConfig.get()
    config.payme_merchant_id = "M1"
    url = links.payme_url(order, config, "uz", "https://x/done/")
    assert _payme_query(url, "https://checkout.paycom.uz/") == (
        f"m=M1;ac.order_id={order.id};a=1500000;l=uz;c=https://x/done/"
    )
    config.payme_test_mode = True
    url = links.payme_url(order, config, "ru", "https://x/done/")
    assert ";l=ru;" in _payme_query(url, "https://test.paycom.uz/")
    assert ";l=uz;" in _payme_query(links.payme_url(order, config, "kr", "u"),
                                    "https://test.paycom.uz/")


def test_click_url_params(student, make_order):
    order = make_order(student, provider="click")
    config = PaymentConfig.get()
    config.click_service_id, config.click_merchant_id = "111", "222"
    url = links.click_url(order, config, "https://x/done/?a=1")
    parsed = urlparse(url)
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == "https://my.click.uz/services/pay"
    q = parse_qs(parsed.query)
    assert q["service_id"] == ["111"] and q["merchant_id"] == ["222"]
    assert q["amount"] == ["15000"] and q["transaction_param"] == [str(order.id)]
    assert q["return_url"] == ["https://x/done/?a=1"]
