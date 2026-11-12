"""PRO to'lovlari — modellar va kalitlarni shifrlash."""

import pytest

from apps.payments import crypto
from apps.payments.models import PaymentConfig


def test_encrypt_roundtrip():
    token = crypto.encrypt("k3y")
    assert token != "k3y"
    assert crypto.decrypt(token) == "k3y"
    # Har safar yangi iv — bir xil matn ikki xil shifr beradi.
    assert crypto.encrypt("k3y") != token


def test_encrypt_empty_is_empty():
    assert crypto.encrypt("") == ""
    assert crypto.decrypt("") == ""


def test_decrypt_garbage_returns_empty():
    assert crypto.decrypt("not-a-token") == ""


@pytest.mark.django_db
def test_config_secret_stored_encrypted():
    config = PaymentConfig.get()
    config.payme_secret_key = "S1-secret"
    config.save()
    raw = PaymentConfig.objects.values_list("payme_secret_key_enc", flat=True).get()
    assert raw and "S1-secret" not in raw
    assert PaymentConfig.get().payme_secret_key == "S1-secret"


@pytest.mark.django_db
def test_config_singleton():
    assert PaymentConfig.get().pk == PaymentConfig.get().pk == 1
    assert PaymentConfig.objects.count() == 1


@pytest.mark.django_db
def test_ready_flags():
    config = PaymentConfig.get()
    assert config.payme_ready() is False and config.click_ready() is False

    config.payme_merchant_id = "M1"
    config.payme_secret_key = "S"
    assert config.payme_ready() is False  # yoqilmagan
    config.payme_enabled = True
    assert config.payme_ready() is True

    config.click_enabled = True
    config.click_service_id = "100"
    config.click_merchant_id = "200"
    assert config.click_ready() is False  # kalit yo'q
    config.click_secret_key = "C"
    assert config.click_ready() is True


@pytest.mark.django_db
def test_allowed_ip_list_parses_commas_and_lines():
    config = PaymentConfig.get()
    config.payme_allowed_ips = "185.234.113.0/24, 10.0.0.1\n 10.0.0.2 "
    assert config.allowed_ip_list() == ["185.234.113.0/24", "10.0.0.1", "10.0.0.2"]
