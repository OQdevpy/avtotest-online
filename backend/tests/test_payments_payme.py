"""Payme Merchant API (JSON-RPC) webhook."""

import base64
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.payments.models import PaymentConfig, ProOrder, ProPlan, ProviderTransaction

URL = "/api/v1/payments/payme/"


@pytest.fixture
def plan(db):
    return ProPlan.objects.create(title_uz="15 kun", days=15, price=15000)


@pytest.fixture
def config(db):
    c = PaymentConfig.get()
    c.payme_enabled, c.payme_merchant_id = True, "M1"
    c.payme_secret_key = "P"
    c.payme_test_secret_key = "T"
    c.save()
    return c


@pytest.fixture
def order(student, plan, config):
    return ProOrder.objects.create(user=student, plan=plan, title="15 kun", days=15,
                                   amount=15000, provider="payme")


def rpc(api, method, params, key="P", **extra):
    token = base64.b64encode(f"Paycom:{key}".encode()).decode()
    r = api.post(URL, {"jsonrpc": "2.0", "id": 7, "method": method, "params": params},
                 format="json", HTTP_AUTHORIZATION=f"Basic {token}", **extra)
    assert r.status_code == 200
    return r.json()


def err(resp):
    return resp["error"]["code"]


def acc(order, amount=None):
    return {"amount": (amount if amount is not None else order.amount * 100),
            "account": {"order_id": order.id}}


def create(api, order, tid="payme-tx-1"):
    return rpc(api, "CreateTransaction", {"id": tid, "time": 1, **acc(order)})


# --- auth ---------------------------------------------------------------------

def test_bad_auth(api, order):
    resp = rpc(api, "CheckPerformTransaction", acc(order), key="wrong")
    assert err(resp) == -32504 and resp["id"] == 7


def test_missing_auth(api, order):
    r = api.post(URL, {"method": "CheckPerformTransaction", "params": acc(order)},
                 format="json")
    assert r.json()["error"]["code"] == -32504


def test_test_key_only_in_test_mode(api, order, config):
    assert err(rpc(api, "CheckPerformTransaction", acc(order), key="T")) == -32504
    config.payme_test_mode = True
    config.save()
    assert rpc(api, "CheckPerformTransaction", acc(order), key="T")["result"]["allow"] is True


def test_disabled_provider_rejects(api, order, config):
    config.payme_enabled = False
    config.save()
    assert err(rpc(api, "CheckPerformTransaction", acc(order))) == -32504


def test_ip_allowlist(api, order, config):
    config.payme_allowed_ips = "10.0.0.0/8"
    config.save()
    blocked = rpc(api, "CheckPerformTransaction", acc(order), HTTP_X_REAL_IP="1.2.3.4")
    assert err(blocked) == -32504
    # X-Forwarded-For ga ishonilmaydi.
    spoofed = rpc(api, "CheckPerformTransaction", acc(order), HTTP_X_REAL_IP="1.2.3.4",
                  HTTP_X_FORWARDED_FOR="10.1.1.1")
    assert err(spoofed) == -32504
    ok = rpc(api, "CheckPerformTransaction", acc(order), HTTP_X_REAL_IP="10.1.1.1")
    assert ok["result"]["allow"] is True


def test_parse_error_and_unknown_method(api, order):
    token = base64.b64encode(b"Paycom:P").decode()
    r = api.post(URL, "not json", content_type="application/json",
                 HTTP_AUTHORIZATION=f"Basic {token}")
    assert r.status_code == 200 and r.json()["error"]["code"] == -32700
    assert err(rpc(api, "Nope", {})) == -32601
    assert err(rpc(api, "ChangePassword", {"password": "x"})) == -32504


# --- CheckPerformTransaction ----------------------------------------------------

def test_check_perform_ok_and_wrong_amount(api, order):
    assert rpc(api, "CheckPerformTransaction", acc(order))["result"]["allow"] is True
    assert err(rpc(api, "CheckPerformTransaction", acc(order, amount=100))) == -31001
    missing = rpc(api, "CheckPerformTransaction", {"amount": 1, "account": {"order_id": 999}})
    assert err(missing) == -31050


def test_plan_price_change_keeps_order_amount(api, order, plan):
    plan.price = 99999
    plan.save()
    assert rpc(api, "CheckPerformTransaction", acc(order))["result"]["allow"] is True


def test_fiscal_detail_when_mxik_set(api, order, config):
    assert "detail" not in rpc(api, "CheckPerformTransaction", acc(order))["result"]
    config.mxik_code, config.package_code, config.vat_percent = "10305013001000000", "1501", 0
    config.save()
    detail = rpc(api, "CheckPerformTransaction", acc(order))["result"]["detail"]
    assert detail["receipt_type"] == 0
    assert detail["items"] == [{"title": "15 kun", "price": 1500000, "count": 1,
                                "code": "10305013001000000", "package_code": "1501",
                                "vat_percent": 0}]


# --- to'liq oqim --------------------------------------------------------------------

def test_full_flow_grants_pro(api, order, student):
    created = create(api, order)["result"]
    assert created["state"] == 1 and created["create_time"] > 0
    performed = rpc(api, "PerformTransaction", {"id": "payme-tx-1"})["result"]
    assert performed["state"] == 2 and performed["perform_time"] > 0
    assert performed["transaction"] == created["transaction"]
    order.refresh_from_db()
    student.refresh_from_db()
    assert order.status == "paid" and student.pro_active
    assert ProviderTransaction.objects.get().state == 2


def test_create_is_idempotent(api, order):
    first = create(api, order)["result"]
    again = create(api, order)["result"]
    assert again == first
    assert ProviderTransaction.objects.count() == 1


def test_perform_twice_grants_once(api, order, student):
    create(api, order)
    rpc(api, "PerformTransaction", {"id": "payme-tx-1"})
    student.refresh_from_db()
    first_until = student.pro_until
    again = rpc(api, "PerformTransaction", {"id": "payme-tx-1"})["result"]
    assert again["state"] == 2
    student.refresh_from_db()
    assert student.pro_until == first_until


def test_perform_unknown_transaction(api, order):
    assert err(rpc(api, "PerformTransaction", {"id": "nope"})) == -31003


def test_second_transaction_busy(api, order):
    create(api, order, tid="a")
    assert err(create(api, order, tid="b")) == -31099


def test_create_for_paid_order(api, order):
    create(api, order)
    rpc(api, "PerformTransaction", {"id": "payme-tx-1"})
    assert err(create(api, order, tid="other")) == -31050


def test_create_timeout(api, order):
    create(api, order)
    ProviderTransaction.objects.update(create_time=timezone.now() - timedelta(hours=13))
    assert err(rpc(api, "PerformTransaction", {"id": "payme-tx-1"})) == -31008
    tx = ProviderTransaction.objects.get()
    order.refresh_from_db()
    assert tx.state == -1 and tx.reason == 4 and order.status == "cancelled"
    # Bekor qilingan tranzaksiyani qayta yaratib bo'lmaydi.
    assert err(create(api, order)) == -31008


def test_cancel_before_perform(api, order):
    create(api, order)
    res = rpc(api, "CancelTransaction", {"id": "payme-tx-1", "reason": 3})["result"]
    assert res["state"] == -1 and res["cancel_time"] > 0
    order.refresh_from_db()
    assert order.status == "cancelled"
    assert err(rpc(api, "PerformTransaction", {"id": "payme-tx-1"})) == -31008
    # Takror cancel — o'sha natija.
    assert rpc(api, "CancelTransaction", {"id": "payme-tx-1", "reason": 3})["result"] == res


def test_cancel_after_perform_revokes(api, order, student):
    create(api, order)
    rpc(api, "PerformTransaction", {"id": "payme-tx-1"})
    res = rpc(api, "CancelTransaction", {"id": "payme-tx-1", "reason": 5})["result"]
    assert res["state"] == -2
    order.refresh_from_db()
    student.refresh_from_db()
    assert order.status == "refunded" and not student.pro_active
    assert ProviderTransaction.objects.get().reason == 5


def test_cancel_after_user_deleted(api, order, student):
    create(api, order)
    rpc(api, "PerformTransaction", {"id": "payme-tx-1"})
    student.delete()
    res = rpc(api, "CancelTransaction", {"id": "payme-tx-1", "reason": 5})["result"]
    assert res["state"] == -2
    order.refresh_from_db()
    assert order.user is None and order.status == "refunded"


def test_check_transaction_fields(api, order):
    create(api, order)
    res = rpc(api, "CheckTransaction", {"id": "payme-tx-1"})["result"]
    assert set(res) == {"create_time", "perform_time", "cancel_time", "transaction",
                        "state", "reason"}
    assert res["state"] == 1 and res["perform_time"] == 0 and res["reason"] is None
    assert err(rpc(api, "CheckTransaction", {"id": "nope"})) == -31003


def test_get_statement_range(api, order):
    create(api, order)
    now_ms = int(timezone.now().timestamp() * 1000)
    hour = 3_600_000
    inside = rpc(api, "GetStatement", {"from": now_ms - hour, "to": now_ms + hour})
    items = inside["result"]["transactions"]
    assert len(items) == 1
    assert items[0]["id"] == "payme-tx-1" and items[0]["amount"] == 1500000
    assert items[0]["account"] == {"order_id": order.id} and items[0]["state"] == 1
    outside = rpc(api, "GetStatement", {"from": now_ms - 3 * hour, "to": now_ms - 2 * hour})
    assert outside["result"]["transactions"] == []
