"""Ilova uchun PRO to'lov API: tariflar, checkout, buyurtma holati, done sahifasi."""

import pytest

from apps.accounts.models import User, guest_phone
from apps.payments.models import PaymentConfig, ProOrder, ProPlan

PLANS = "/api/v1/payments/plans/"
CHECKOUT = "/api/v1/payments/checkout/"


@pytest.fixture
def plan(db):
    return ProPlan.objects.create(title_uz="15 kun", title_ru="15 дней", days=15,
                                  price=15000, order=1)


@pytest.fixture
def config(db):
    c = PaymentConfig.get()
    c.payme_enabled, c.payme_merchant_id = True, "M1"
    c.payme_secret_key = "P"
    c.click_enabled, c.click_service_id, c.click_merchant_id = True, "11", "22"
    c.click_secret_key = "C"
    c.save()
    return c


@pytest.fixture
def client(api, auth, student):
    return auth(api, student)


def test_plans_lists_active_only(client, plan, config):
    ProPlan.objects.create(title_uz="Eski", days=30, price=1, is_active=False)
    r = client.get(PLANS, {"lang": "ru", "platform": "android"})
    assert r.status_code == 200
    assert r.data["plans"] == [{"id": plan.id, "title": "15 дней", "days": 15, "price": 15000}]
    assert r.data["providers"] == ["payme", "click"]


def test_plans_ios_hidden_by_default(client, plan, config):
    r = client.get(PLANS, {"platform": "ios"})
    assert r.data["providers"] == []
    assert len(r.data["plans"]) == 1


def test_plans_requires_auth(api, plan):
    assert api.get(PLANS).status_code == 401


def test_checkout_creates_order_with_snapshot(client, student, plan, config):
    r = client.post(CHECKOUT, {"plan": plan.id, "provider": "payme", "platform": "android"},
                    format="json")
    assert r.status_code == 201, r.data
    order = ProOrder.objects.get(pk=r.data["order_id"])
    assert order.user == student and order.status == "pending"
    assert order.amount == 15000 and order.days == 15 and order.title == "15 kun"
    assert r.data["amount"] == 15000 and r.data["days"] == 15 and r.data["provider"] == "payme"
    assert r.data["payment_url"].startswith("https://checkout.paycom.uz/")


def test_checkout_click_url(client, plan, config):
    r = client.post(CHECKOUT, {"plan": plan.id, "provider": "click", "platform": "android"},
                    format="json")
    assert r.status_code == 201
    assert r.data["payment_url"].startswith("https://my.click.uz/services/pay?")
    assert "payments%2Fdone%2F" in r.data["payment_url"]


def test_checkout_guest_forbidden(api, auth, plan, config):
    guest = User.objects.create(phone=guest_phone(), role="guest")
    r = auth(api, guest).post(CHECKOUT, {"plan": plan.id, "provider": "payme",
                                         "platform": "android"}, format="json")
    assert r.status_code == 403
    assert r.data["code"] == "register_required"


def test_checkout_disabled_provider(client, plan, config):
    config.click_enabled = False
    config.save()
    r = client.post(CHECKOUT, {"plan": plan.id, "provider": "click", "platform": "android"},
                    format="json")
    assert r.status_code == 400 and r.data["code"] == "provider_unavailable"


def test_checkout_ios_not_selling(client, plan, config):
    r = client.post(CHECKOUT, {"plan": plan.id, "provider": "payme", "platform": "ios"},
                    format="json")
    assert r.status_code == 400 and r.data["code"] == "provider_unavailable"


def test_checkout_inactive_plan(client, plan, config):
    plan.is_active = False
    plan.save()
    r = client.post(CHECKOUT, {"plan": plan.id, "provider": "payme", "platform": "android"},
                    format="json")
    assert r.status_code == 400 and r.data["code"] == "plan_unavailable"


def test_checkout_unknown_plan(client, config):
    r = client.post(CHECKOUT, {"plan": 999, "provider": "payme", "platform": "android"},
                    format="json")
    assert r.status_code == 400 and r.data["code"] == "plan_unavailable"


def test_checkout_unlimited_user(client, student, plan, config):
    student.is_pro, student.pro_until = True, None
    student.save()
    r = client.post(CHECKOUT, {"plan": plan.id, "provider": "payme", "platform": "android"},
                    format="json")
    assert r.status_code == 400 and r.data["code"] == "already_unlimited"


def test_checkout_throttled(client, plan, config):
    body = {"plan": plan.id, "provider": "payme", "platform": "android"}
    codes = [client.post(CHECKOUT, body, format="json").status_code for _ in range(21)]
    assert codes[:20] == [201] * 20
    assert codes[20] == 429


def test_order_detail_owner_only(api, auth, student, other_student, plan, config):
    r = auth(api, student).post(CHECKOUT, {"plan": plan.id, "provider": "payme",
                                           "platform": "android"}, format="json")
    url = f"/api/v1/payments/orders/{r.data['order_id']}/"
    own = api.get(url)
    assert own.status_code == 200
    assert own.data["status"] == "pending" and own.data["pro_active"] is False
    assert set(own.data) == {"id", "status", "days", "amount", "provider", "paid_at",
                             "pro_until", "pro_active"}
    assert auth(api, other_student).get(url).status_code == 404


def test_done_page_public(api, db):
    r = api.get("/api/v1/payments/done/")
    assert r.status_code == 200
    assert r["Content-Type"].startswith("text/html")
    assert "ilovaga qayting" in r.content.decode().lower()
