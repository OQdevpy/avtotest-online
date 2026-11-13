"""Click SHOP API (Prepare/Complete) webhook."""

import hashlib

import pytest

from apps.payments.models import PaymentConfig, ProOrder, ProPlan, ProviderTransaction

PREPARE = "/api/v1/payments/click/prepare/"
COMPLETE = "/api/v1/payments/click/complete/"
SECRET = "CLICKSECRET"


@pytest.fixture
def plan(db):
    return ProPlan.objects.create(title_uz="15 kun", days=15, price=15000)


@pytest.fixture
def config(db):
    c = PaymentConfig.get()
    c.click_enabled = True
    c.click_service_id, c.click_merchant_id = "111", "222"
    c.click_secret_key = SECRET
    c.save()
    return c


@pytest.fixture
def order(student, plan, config):
    return ProOrder.objects.create(user=student, plan=plan, title="15 kun", days=15,
                                   amount=15000, provider="click")


def signed(data, secret=SECRET):
    prepare_id = data.get("merchant_prepare_id", "") if str(data["action"]) == "1" else ""
    raw = (f"{data['click_trans_id']}{data['service_id']}{secret}{data['merchant_trans_id']}"
           f"{prepare_id}{data['amount']}{data['action']}{data['sign_time']}")
    return {**data, "sign_string": hashlib.md5(raw.encode()).hexdigest()}


def base(order, action, **over):
    data = {
        "click_trans_id": "9001", "service_id": "111", "click_paydoc_id": "5001",
        "merchant_trans_id": str(order.id), "amount": "15000.00", "action": str(action),
        "error": "0", "error_note": "Success", "sign_time": "2026-11-13 10:00:00",
    }
    data.update(over)
    return data


def post(api, url, data):
    r = api.post(url, data)  # form-encoded
    assert r.status_code == 200
    return r.json()


def prepare(api, order, **over):
    return post(api, PREPARE, signed(base(order, 0, **over)))


def complete(api, order, prepare_id, **over):
    return post(api, COMPLETE, signed(base(order, 1, merchant_prepare_id=str(prepare_id), **over)))


# --- imzo va sozlamalar -------------------------------------------------------

def test_bad_sign(api, order):
    data = signed(base(order, 0), secret="wrong")
    assert post(api, PREPARE, data)["error"] == -1


def test_wrong_service_id(api, order):
    assert prepare(api, order, service_id="999")["error"] == -1


def test_disabled_provider(api, order, config):
    config.click_enabled = False
    config.save()
    assert prepare(api, order)["error"] == -1


def test_missing_field(api, order):
    data = signed(base(order, 0))
    del data["click_paydoc_id"]
    assert post(api, PREPARE, data)["error"] == -8


def test_wrong_action(api, order):
    assert post(api, PREPARE, signed(base(order, 5)))["error"] == -3


# --- prepare ------------------------------------------------------------------

def test_prepare_ok(api, order):
    resp = prepare(api, order)
    assert resp["error"] == 0
    tx = ProviderTransaction.objects.get(provider="click", external_id="9001")
    assert resp["merchant_prepare_id"] == tx.id
    assert resp["click_trans_id"] == 9001 and resp["merchant_trans_id"] == str(order.id)
    assert tx.state == ProviderTransaction.CREATED and tx.extra["click_paydoc_id"] == "5001"


def test_prepare_repeat_returns_same_tx(api, order):
    first = prepare(api, order)
    second = prepare(api, order)
    assert second["error"] == 0
    assert second["merchant_prepare_id"] == first["merchant_prepare_id"]


def test_prepare_wrong_amount(api, order):
    assert prepare(api, order, amount="100.00")["error"] == -2


def test_prepare_unknown_order(api, order):
    assert prepare(api, order, merchant_trans_id="999999")["error"] == -5


def test_prepare_payme_order_not_found(api, order):
    order.provider = "payme"
    order.save()
    assert prepare(api, order)["error"] == -5


def test_prepare_cancelled_order(api, order):
    order.status = ProOrder.Status.CANCELLED
    order.save()
    assert prepare(api, order)["error"] == -9


# --- complete -----------------------------------------------------------------

def test_complete_grants_pro(api, order, student):
    pid = prepare(api, order)["merchant_prepare_id"]
    resp = complete(api, order, pid)
    assert resp["error"] == 0 and resp["merchant_confirm_id"] == pid
    order.refresh_from_db()
    student.refresh_from_db()
    assert order.status == ProOrder.Status.PAID
    assert student.pro_active
    assert ProviderTransaction.objects.get(pk=pid).state == ProviderTransaction.PERFORMED
    assert "fiscal_items" not in resp


def test_complete_with_click_error_cancels(api, order, student):
    pid = prepare(api, order)["merchant_prepare_id"]
    resp = complete(api, order, pid, error="-5017", error_note="Insufficient funds")
    assert resp["error"] == -9
    order.refresh_from_db()
    student.refresh_from_db()
    assert order.status == ProOrder.Status.CANCELLED
    assert not student.pro_active
    assert ProviderTransaction.objects.get(pk=pid).state == ProviderTransaction.CANCELLED


def test_complete_twice_already_paid(api, order, student):
    pid = prepare(api, order)["merchant_prepare_id"]
    complete(api, order, pid)
    student.refresh_from_db()
    until = student.pro_until
    assert complete(api, order, pid)["error"] == -4
    student.refresh_from_db()
    assert student.pro_until == until


def test_complete_mismatched_trans_id(api, order):
    pid = prepare(api, order)["merchant_prepare_id"]
    assert complete(api, order, pid, click_trans_id="7777")["error"] == -6


def test_complete_unknown_prepare_id(api, order):
    prepare(api, order)
    assert complete(api, order, 999999)["error"] == -6


def test_complete_fiscal_items_when_mxik_set(api, order, config):
    config.mxik_code, config.package_code, config.vat_percent = "10305001001000000", "1500", 12
    config.save()
    pid = prepare(api, order)["merchant_prepare_id"]
    resp = complete(api, order, pid)
    assert resp["error"] == 0
    item = resp["fiscal_items"][0]
    assert item["SPIC"] == "10305001001000000" and item["PackageCode"] == "1500"
    assert item["Price"] == 15000 * 100 and item["Amount"] == 1 and item["VATPercent"] == 12
