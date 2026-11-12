"""To'lov havolalari — faqat backend tuzadi (merchant ma'lumotlari ilovaga chiqmaydi)."""

import base64
from urllib.parse import urlencode

from .models import PaymentConfig, ProOrder

PAYME_CHECKOUT = "https://checkout.paycom.uz/"
PAYME_TEST_CHECKOUT = "https://test.paycom.uz/"
CLICK_PAY = "https://my.click.uz/services/pay"


def payme_url(order: ProOrder, config: PaymentConfig, lang: str, return_url: str) -> str:
    """Payme checkout: base64("m=..;ac.order_id=..;a=<tiyin>;l=..;c=..")."""
    payme_lang = "ru" if lang == "ru" else "uz"
    params = (
        f"m={config.payme_merchant_id};ac.order_id={order.id};a={order.amount * 100};"
        f"l={payme_lang};c={return_url}"
    )
    base = PAYME_TEST_CHECKOUT if config.payme_test_mode else PAYME_CHECKOUT
    return base + base64.b64encode(params.encode()).decode()


def click_url(order: ProOrder, config: PaymentConfig, return_url: str) -> str:
    query = urlencode({
        "service_id": config.click_service_id,
        "merchant_id": config.click_merchant_id,
        "amount": order.amount,
        "transaction_param": order.id,
        "return_url": return_url,
    })
    return f"{CLICK_PAY}?{query}"
