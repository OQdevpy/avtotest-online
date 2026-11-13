"""Click SHOP API webhook — `POST /api/v1/payments/click/prepare/` va `.../complete/`.

Kirish form-encoded, javob JSON (`error` — int). `merchant_trans_id` — `ProOrder.id`,
summa so'mda (`"15000.00"`). Imzo xom POST qiymatlaridan md5 bilan tekshiriladi.
Muhim: `complete` da Click o'zi `error < 0` yuborsa pul tushmagan — PRO berilmaydi.
"""

import hashlib
import logging
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from drf_spectacular.utils import extend_schema
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import PaymentConfig, ProOrder, Provider, ProviderTransaction

logger = logging.getLogger(__name__)

PREPARE, COMPLETE = "0", "1"

OK = 0
SIGN_FAILED = -1
INVALID_AMOUNT = -2
ACTION_NOT_FOUND = -3
ALREADY_PAID = -4
ORDER_NOT_FOUND = -5
TX_NOT_FOUND = -6
BAD_REQUEST = -8
CANCELLED = -9

NOTES = {
    OK: "Success",
    SIGN_FAILED: "SIGN CHECK FAILED!",
    INVALID_AMOUNT: "Incorrect parameter amount",
    ACTION_NOT_FOUND: "Action not found",
    ALREADY_PAID: "Already paid",
    ORDER_NOT_FOUND: "User does not exist",
    TX_NOT_FOUND: "Transaction does not exist",
    BAD_REQUEST: "Error in request from click",
    CANCELLED: "Transaction cancelled",
}

REQUIRED = ("click_trans_id", "service_id", "click_paydoc_id", "merchant_trans_id",
            "amount", "action", "error", "error_note", "sign_time", "sign_string")


class ClickError(Exception):
    def __init__(self, code: int):
        super().__init__(code)
        self.code = code


def _int_or_raw(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def check_sign(data, config: PaymentConfig) -> bool:
    prepare_id = data.get("merchant_prepare_id", "") if data.get("action") == COMPLETE else ""
    raw = (f"{data['click_trans_id']}{data['service_id']}{config.click_secret_key}"
           f"{data['merchant_trans_id']}{prepare_id}{data['amount']}{data['action']}"
           f"{data['sign_time']}")
    expected = hashlib.md5(raw.encode()).hexdigest()
    return constant_time_compare(expected, str(data.get("sign_string", "")).lower())


def _locked_order(data) -> ProOrder:
    try:
        pk = int(data["merchant_trans_id"])
    except (TypeError, ValueError):
        raise ClickError(ORDER_NOT_FOUND) from None
    order = ProOrder.objects.select_for_update().filter(pk=pk, provider=Provider.CLICK).first()
    if order is None:
        raise ClickError(ORDER_NOT_FOUND)
    return order


def _check_order(data, order: ProOrder) -> None:
    try:
        amount = Decimal(data["amount"])
    except (InvalidOperation, TypeError, ValueError):
        raise ClickError(BAD_REQUEST) from None
    if amount != order.amount:
        raise ClickError(INVALID_AMOUNT)
    if order.status == ProOrder.Status.PAID:
        raise ClickError(ALREADY_PAID)
    if order.status != ProOrder.Status.PENDING:
        raise ClickError(CANCELLED)


def fiscal_items(order: ProOrder, config: PaymentConfig) -> list[dict]:
    """Click OFD chek bandlari; narx tiyinda."""
    return [{
        "Name": order.title, "SPIC": config.mxik_code, "PackageCode": config.package_code,
        "Price": order.amount * 100, "Amount": 1, "VATPercent": config.vat_percent or 0,
    }]


def prepare(data, config: PaymentConfig) -> dict:
    order = _locked_order(data)
    _check_order(data, order)
    external_id = str(data["click_trans_id"])
    tx = (ProviderTransaction.objects.select_for_update()
          .filter(provider=Provider.CLICK, external_id=external_id).first())
    if tx is None:
        tx = ProviderTransaction.objects.create(
            order=order, provider=Provider.CLICK, external_id=external_id,
            state=ProviderTransaction.CREATED, amount=order.amount, create_time=timezone.now(),
            extra={"click_paydoc_id": str(data["click_paydoc_id"])},
        )
    elif tx.order_id != order.id or tx.state != ProviderTransaction.CREATED:
        raise ClickError(TX_NOT_FOUND)
    return {"merchant_prepare_id": tx.id}


def complete(data, config: PaymentConfig) -> dict:
    order = _locked_order(data)
    _check_order(data, order)
    try:
        prepare_id = int(data.get("merchant_prepare_id"))
    except (TypeError, ValueError):
        raise ClickError(TX_NOT_FOUND) from None
    tx = (ProviderTransaction.objects.select_for_update()
          .filter(pk=prepare_id, provider=Provider.CLICK, order=order).first())
    if tx is None or tx.external_id != str(data["click_trans_id"]):
        raise ClickError(TX_NOT_FOUND)
    if tx.state != ProviderTransaction.CREATED:
        raise ClickError(CANCELLED)

    try:
        click_error = int(data["error"])
    except (TypeError, ValueError):
        raise ClickError(BAD_REQUEST) from None
    if click_error < 0:
        # Pul tushmagan: PRO berilmaydi, buyurtma bekor.
        tx.state = ProviderTransaction.CANCELLED
        tx.cancel_time = timezone.now()
        tx.reason = click_error
        tx.save(update_fields=["state", "cancel_time", "reason"])
        services.cancel_pending(order)
        raise ClickError(CANCELLED)

    services.grant_pro(order)
    tx.state = ProviderTransaction.PERFORMED
    tx.perform_time = timezone.now()
    tx.save(update_fields=["state", "perform_time"])
    result = {"merchant_confirm_id": tx.id}
    if config.mxik_code:
        result["fiscal_items"] = fiscal_items(order, config)
    return result


class _ClickView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()
    parser_classes = (FormParser, MultiPartParser)
    http_method_names = ("post",)
    action: str = ""
    handler = None

    def post(self, request):
        data = {k: request.data.get(k) for k in request.data}
        body = {"click_trans_id": _int_or_raw(data.get("click_trans_id")),
                "merchant_trans_id": data.get("merchant_trans_id")}

        def reply(code: int, **extra):
            return Response({**body, **extra, "error": code, "error_note": NOTES[code]})

        if any(data.get(k) in (None, "") for k in REQUIRED):
            return reply(BAD_REQUEST)
        if data["action"] not in (PREPARE, COMPLETE) or data["action"] != self.action:
            return reply(ACTION_NOT_FOUND)
        if self.action == COMPLETE and not data.get("merchant_prepare_id"):
            return reply(BAD_REQUEST)

        config = PaymentConfig.get()
        if (not config.click_ready() or str(data["service_id"]) != config.click_service_id
                or not check_sign(data, config)):
            logger.warning("click: imzo/sozlama xatosi")
            return reply(SIGN_FAILED)

        # Xato ham atomic ichida ushlanadi: bekor qilish saqlanib qolsin.
        with transaction.atomic():
            try:
                result = type(self).handler(data, config)
            except ClickError as e:
                logger.info("click action=%s -> %s", self.action, e.code)
                return reply(e.code)
        logger.info("click action=%s -> ok", self.action)
        return reply(OK, **result)


@extend_schema(exclude=True)
class ClickPrepareView(_ClickView):
    action = PREPARE
    handler = staticmethod(prepare)


@extend_schema(exclude=True)
class ClickCompleteView(_ClickView):
    action = COMPLETE
    handler = staticmethod(complete)
