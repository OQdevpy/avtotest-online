"""Payme Merchant API (JSON-RPC 2.0) webhook — `POST /api/v1/payments/payme/`.

`account.order_id` — `ProOrder.id`; summa tiyinda (`so'm * 100`). Javob doim
HTTP 200, xato JSON-RPC `error` ichida. Har metod `transaction.atomic()` ichida,
buyurtma va tranzaksiya qatorlari `select_for_update()` bilan qulflanadi.
"""

import base64
import binascii
import ipaddress
import json
import logging
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import PaymentConfig, ProOrder, Provider, ProviderTransaction

logger = logging.getLogger(__name__)

TIMEOUT = timedelta(milliseconds=43_200_000)  # 12 soat
REASON_TIMEOUT = 4

AUTH = -32504
PARSE = -32700
METHOD_NOT_FOUND = -32601
INVALID_AMOUNT = -31001
TX_NOT_FOUND = -31003
CANNOT_PERFORM = -31008
ORDER_NOT_FOUND = -31050
ORDER_BUSY = -31099

MESSAGES = {
    AUTH: ("Ruxsat yo'q", "Недостаточно привилегий", "Insufficient privileges"),
    PARSE: ("So'rovni o'qib bo'lmadi", "Ошибка разбора запроса", "Parse error"),
    METHOD_NOT_FOUND: ("Metod topilmadi", "Метод не найден", "Method not found"),
    INVALID_AMOUNT: ("Noto'g'ri summa", "Неверная сумма", "Invalid amount"),
    TX_NOT_FOUND: ("Tranzaksiya topilmadi", "Транзакция не найдена", "Transaction not found"),
    CANNOT_PERFORM: ("Amalni bajarib bo'lmaydi", "Невозможно выполнить операцию",
                     "Unable to perform operation"),
    ORDER_NOT_FOUND: ("Buyurtma topilmadi yoki to'lab bo'lmaydi",
                      "Заказ не найден или недоступен", "Order not found or unavailable"),
    ORDER_BUSY: ("Buyurtma boshqa to'lov bilan band", "Заказ ожидает другую оплату",
                 "Order is busy with another transaction"),
}


class PaymeError(Exception):
    def __init__(self, code: int, data: str | None = None):
        super().__init__(code)
        self.code = code
        self.data = data

    def as_dict(self) -> dict:
        uz, ru, en = MESSAGES[self.code]
        error = {"code": self.code, "message": {"uz": uz, "ru": ru, "en": en}}
        if self.data:
            error["data"] = self.data
        return error


def _ms(dt) -> int:
    return int(dt.timestamp() * 1000) if dt else 0


def _from_ms(value) -> datetime:
    return datetime.fromtimestamp(int(value) / 1000, tz=dt_timezone.utc)


def client_ip(request) -> str:
    """nginx `X-Real-IP` ni `$remote_addr` bilan yozadi; `X-Forwarded-For` ga ishonilmaydi."""
    return (request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR") or "").strip()


def ip_allowed(request, config: PaymentConfig) -> bool:
    allowed = config.allowed_ip_list()
    if not allowed:
        return True
    try:
        ip = ipaddress.ip_address(client_ip(request))
    except ValueError:
        return False
    for entry in allowed:
        try:
            if ip in ipaddress.ip_network(entry, strict=False):
                return True
        except ValueError:
            continue
    return False


def authorized(request, config: PaymentConfig) -> bool:
    if not config.payme_ready() or not ip_allowed(request, config):
        return False
    header = request.META.get("HTTP_AUTHORIZATION", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "basic" or not token:
        return False
    try:
        login, _, password = base64.b64decode(token.strip()).decode().partition(":")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return False
    keys = [config.payme_secret_key]
    if config.payme_test_mode and config.payme_test_secret_key:
        keys.append(config.payme_test_secret_key)
    password_ok = any(constant_time_compare(password, key) for key in keys if key)
    return constant_time_compare(login, "Paycom") and password_ok


# --- yordamchilar --------------------------------------------------------------------

def _locked_order(pk) -> ProOrder | None:
    return ProOrder.objects.select_for_update().filter(pk=pk).first()


def _order_from_account(params) -> ProOrder:
    raw = (params.get("account") or {}).get("order_id")
    try:
        pk = int(raw)
    except (TypeError, ValueError):
        raise PaymeError(ORDER_NOT_FOUND, "order_id") from None
    order = ProOrder.objects.select_for_update().filter(pk=pk, provider=Provider.PAYME).first()
    if order is None:
        raise PaymeError(ORDER_NOT_FOUND, "order_id")
    return order


def _check_amount(params, order: ProOrder) -> None:
    try:
        amount = int(params.get("amount"))
    except (TypeError, ValueError):
        raise PaymeError(INVALID_AMOUNT) from None
    if amount != order.amount * 100:
        raise PaymeError(INVALID_AMOUNT)


def _locked_tx(params) -> ProviderTransaction:
    external_id = str(params.get("id") or "")
    tx = (ProviderTransaction.objects.select_for_update()
          .filter(provider=Provider.PAYME, external_id=external_id).first())
    if not external_id or tx is None:
        raise PaymeError(TX_NOT_FOUND)
    return tx


def _expired(tx: ProviderTransaction) -> bool:
    return timezone.now() - tx.create_time > TIMEOUT


def _cancel(tx: ProviderTransaction, order: ProOrder, reason) -> None:
    if tx.state == ProviderTransaction.CREATED:
        tx.state = ProviderTransaction.CANCELLED
        services.cancel_pending(order)
    elif tx.state == ProviderTransaction.PERFORMED:
        tx.state = ProviderTransaction.CANCELLED_AFTER_PERFORM
        services.revoke_pro(order)
    tx.reason = reason
    tx.cancel_time = timezone.now()
    tx.save(update_fields=["state", "reason", "cancel_time"])


def _created_result(tx: ProviderTransaction) -> dict:
    return {"create_time": _ms(tx.create_time), "transaction": str(tx.id), "state": tx.state}


# --- metodlar -------------------------------------------------------------------------

def check_perform_transaction(params, config: PaymentConfig) -> dict:
    order = _order_from_account(params)
    _check_amount(params, order)
    if order.status != ProOrder.Status.PENDING:
        raise PaymeError(ORDER_NOT_FOUND, "order_id")
    result = {"allow": True}
    if config.mxik_code:
        item = {"title": order.title, "price": order.amount * 100, "count": 1,
                "code": config.mxik_code, "package_code": config.package_code,
                "vat_percent": config.vat_percent or 0}
        result["detail"] = {"receipt_type": 0, "items": [item]}
    return result


def create_transaction(params, config: PaymentConfig) -> dict:
    external_id = str(params.get("id") or "")
    existing = (ProviderTransaction.objects.select_for_update()
                .filter(provider=Provider.PAYME, external_id=external_id).first())
    if existing is not None:
        if existing.state != ProviderTransaction.CREATED:
            raise PaymeError(CANNOT_PERFORM)
        if _expired(existing):
            _cancel(existing, _locked_order(existing.order_id), REASON_TIMEOUT)
            raise PaymeError(CANNOT_PERFORM)
        return _created_result(existing)

    order = _order_from_account(params)
    _check_amount(params, order)
    if order.status != ProOrder.Status.PENDING:
        raise PaymeError(ORDER_NOT_FOUND, "order_id")
    if not external_id:
        raise PaymeError(TX_NOT_FOUND)
    busy = order.transactions.filter(provider=Provider.PAYME,
                                     state=ProviderTransaction.CREATED).exists()
    if busy:
        raise PaymeError(ORDER_BUSY, "order_id")
    tx = ProviderTransaction.objects.create(
        order=order, provider=Provider.PAYME, external_id=external_id,
        state=ProviderTransaction.CREATED, amount=order.amount, create_time=timezone.now(),
        extra={"payme_time": params.get("time")},
    )
    return _created_result(tx)


def perform_transaction(params, config: PaymentConfig) -> dict:
    tx = _locked_tx(params)
    order = _locked_order(tx.order_id)
    if tx.state == ProviderTransaction.PERFORMED:
        return {"transaction": str(tx.id), "perform_time": _ms(tx.perform_time),
                "state": tx.state}
    if tx.state != ProviderTransaction.CREATED:
        raise PaymeError(CANNOT_PERFORM)
    if _expired(tx):
        _cancel(tx, order, REASON_TIMEOUT)
        raise PaymeError(CANNOT_PERFORM)
    if order.status != ProOrder.Status.PENDING:
        raise PaymeError(CANNOT_PERFORM)
    services.grant_pro(order)
    tx.state = ProviderTransaction.PERFORMED
    tx.perform_time = timezone.now()
    tx.save(update_fields=["state", "perform_time"])
    return {"transaction": str(tx.id), "perform_time": _ms(tx.perform_time), "state": tx.state}


def cancel_transaction(params, config: PaymentConfig) -> dict:
    tx = _locked_tx(params)
    if tx.state in (ProviderTransaction.CREATED, ProviderTransaction.PERFORMED):
        _cancel(tx, _locked_order(tx.order_id), params.get("reason"))
    return {"transaction": str(tx.id), "cancel_time": _ms(tx.cancel_time), "state": tx.state}


def check_transaction(params, config: PaymentConfig) -> dict:
    tx = _locked_tx(params)
    return {
        "create_time": _ms(tx.create_time), "perform_time": _ms(tx.perform_time),
        "cancel_time": _ms(tx.cancel_time), "transaction": str(tx.id), "state": tx.state,
        "reason": tx.reason,
    }


def get_statement(params, config: PaymentConfig) -> dict:
    try:
        start, end = _from_ms(params["from"]), _from_ms(params["to"])
    except (KeyError, TypeError, ValueError, OverflowError):
        raise PaymeError(PARSE) from None
    txs = ProviderTransaction.objects.filter(
        provider=Provider.PAYME, create_time__gte=start, create_time__lte=end,
    ).order_by("create_time")
    return {"transactions": [
        {
            "id": tx.external_id, "time": (tx.extra or {}).get("payme_time") or _ms(tx.create_time),
            "amount": tx.amount * 100, "account": {"order_id": tx.order_id},
            "create_time": _ms(tx.create_time), "perform_time": _ms(tx.perform_time),
            "cancel_time": _ms(tx.cancel_time), "transaction": str(tx.id),
            "state": tx.state, "reason": tx.reason,
        }
        for tx in txs
    ]}


def change_password(params, config: PaymentConfig) -> dict:
    # Kalit faqat admin paneldan o'zgaradi.
    raise PaymeError(AUTH)


METHODS = {
    "CheckPerformTransaction": check_perform_transaction,
    "CreateTransaction": create_transaction,
    "PerformTransaction": perform_transaction,
    "CancelTransaction": cancel_transaction,
    "CheckTransaction": check_transaction,
    "GetStatement": get_statement,
    "ChangePassword": change_password,
}


@extend_schema(exclude=True)
class PaymeWebhookView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()
    http_method_names = ("post",)

    def post(self, request):
        try:
            payload = json.loads(request.body or b"")
        except (ValueError, UnicodeDecodeError):
            payload = None
        rpc_id = payload.get("id") if isinstance(payload, dict) else None

        def reply(**body):
            return Response({"jsonrpc": "2.0", "id": rpc_id, **body})

        config = PaymentConfig.get()
        if not authorized(request, config):
            logger.warning("payme: ruxsatsiz so'rov ip=%s", client_ip(request))
            return reply(error=PaymeError(AUTH).as_dict())
        if not isinstance(payload, dict) or not isinstance(payload.get("params"), dict):
            return reply(error=PaymeError(PARSE).as_dict())

        method = payload.get("method")
        handler = METHODS.get(method)
        if handler is None:
            return reply(error=PaymeError(METHOD_NOT_FOUND).as_dict())

        # Xato ham atomic ichida ushlanadi: 12 soatlik bekor qilish saqlanib qolsin.
        with transaction.atomic():
            try:
                result = handler(payload["params"], config)
            except PaymeError as e:
                logger.info("payme %s -> %s", method, e.code)
                return reply(error=e.as_dict())
        logger.info("payme %s -> ok", method)
        return reply(result=result)
