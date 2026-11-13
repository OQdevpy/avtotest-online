"""Django admin: to'lov kalitlari faqat superuser'ga, maxfiy qiymat sahifada chiqmaydi."""

import pytest

from apps.payments.models import PaymentConfig, ProOrder, ProPlan

CONFIG_URL = "/admin/payments/paymentconfig/1/change/"


@pytest.fixture(autouse=True)
def _plain_static(settings):
    # Admin sahifasi render qilinadi; testda `collectstatic` manifesti yo'q.
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }


@pytest.fixture
def superuser(django_user_model):
    return django_user_model.objects.create_user(
        "+998901110099", "pass12345", full_name="Super", role="admin",
        is_staff=True, is_superuser=True,
    )


@pytest.fixture
def config(db):
    c = PaymentConfig.get()
    c.payme_enabled, c.payme_merchant_id = True, "M1"
    c.payme_secret_key = "TOPSECRET"
    c.save()
    return c


def form_data(**over):
    data = {"sell_android": "on", "payme_enabled": "on", "payme_merchant_id": "M1",
            "payme_allowed_ips": "", "click_service_id": "", "click_merchant_id": "",
            "click_merchant_user_id": "", "mxik_code": "", "package_code": "",
            "vat_percent": "", "payme_secret_key": "", "payme_test_secret_key": "",
            "click_secret_key": ""}
    data.update(over)
    return data


def test_config_hidden_from_staff_admin(client, admin_user, config):
    client.force_login(admin_user)
    assert client.get(CONFIG_URL).status_code == 403


def test_changelist_redirects_to_singleton(client, superuser, db):
    client.force_login(superuser)
    r = client.get("/admin/payments/paymentconfig/")
    assert r.status_code == 302 and r["Location"].endswith(CONFIG_URL)


def test_config_form_never_renders_secret(client, superuser, config):
    client.force_login(superuser)
    r = client.get(CONFIG_URL)
    assert r.status_code == 200
    body = r.content.decode()
    assert "TOPSECRET" not in body
    assert "payme_secret_key_enc" not in body
    assert "o'rnatilgan" in body


def test_blank_secret_keeps_old(client, superuser, config):
    client.force_login(superuser)
    r = client.post(CONFIG_URL, form_data())
    assert r.status_code == 302, r.content.decode()[:2000]
    assert PaymentConfig.get().payme_secret_key == "TOPSECRET"

    r = client.post(CONFIG_URL, form_data(payme_secret_key="NEWKEY"))
    assert r.status_code == 302
    assert PaymentConfig.get().payme_secret_key == "NEWKEY"


def test_orders_read_only(client, superuser, student):
    plan = ProPlan.objects.create(title_uz="15 kun", days=15, price=15000)
    order = ProOrder.objects.create(user=student, plan=plan, title="15 kun", days=15,
                                    amount=15000, provider="payme")
    client.force_login(superuser)
    url = f"/admin/payments/proorder/{order.id}/change/"
    assert client.get(url).status_code == 200
    assert client.post(url, {"status": "paid"}).status_code == 403
    order.refresh_from_db()
    assert order.status == ProOrder.Status.PENDING


def test_plans_list_editable(client, superuser, db):
    ProPlan.objects.create(title_uz="15 kun", days=15, price=15000)
    client.force_login(superuser)
    assert client.get("/admin/payments/proplan/").status_code == 200
