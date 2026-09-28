"""Telegram orqali tasdiqlash kodi endpointlari.

Oqim:
    1) POST /api/v1/auth/send-code/    {phone, purpose}          -> {expires_in}
    2) POST /api/v1/auth/verify-code/  {phone, purpose, code}    -> {token}
    3) POST /api/v1/auth/reset-password/ {phone, token, password} -> 204

Kodlar Redis'da (TTL bilan) saqlanadi — ``otpstore`` moduliga qarang.
Kod aynan telefon raqamiga bog'langan Telegram hisobiga yuboriladi va
hech qachon javobda qaytarilmaydi.
"""

from __future__ import annotations

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User

from . import otpstore, telegram
from .models import TelegramAccount
from .serializers import (
    ResetPasswordSerializer,
    SendCodeSerializer,
    VerifyCodeSerializer,
)


def _error(code: str, detail: str, http_status: int = status.HTTP_400_BAD_REQUEST):
    """Frontend `code` bo'yicha shoxlanadi; `detail` — o'qiladigan matn."""
    return Response({"code": code, "detail": detail}, status=http_status)


@extend_schema(tags=["auth"])
class SendCodeView(APIView):
    """«Kodni olish»: bog'langan Telegram hisobiga 6 xonali kod yuboradi."""

    permission_classes = [permissions.AllowAny]
    serializer_class = SendCodeSerializer

    def post(self, request):
        # Foydalanuvchi so'rovi bo'yicha ?phone= ni ham qabul qilamiz.
        data = {**request.query_params.dict(), **request.data}
        serializer = SendCodeSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone"]
        purpose = serializer.validated_data["purpose"]

        account = (
            TelegramAccount.objects.filter(phone=phone)
            .order_by("-verified_at", "-created_at")
            .first()
        )
        if account is None:
            # Alohida error kodi — ilova @AvtotestTayyorlovBot'ga yo'naltiradi.
            return _error(
                "telegram_not_linked",
                "Bu raqam Telegram'ga bog'lanmagan. Iltimos, "
                f"{telegram.BOT_LINK} ni oching, /start bosing va "
                "«Kontaktni ulashish» orqali raqamingizni bog'lang.",
            )

        # Qayta yuborish uchun cooldown (Redis TTL).
        left = otpstore.cooldown_left(purpose, phone)
        if left > 0:
            return _error(
                "cooldown",
                f"Iltimos, {left} soniyadan so'ng qayta urinib ko'ring.",
                http_status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        plain = otpstore.issue_code(purpose, phone, account.telegram_id)
        text = telegram.t(
            "code_message",
            account.language,
            code=plain,
            minutes=otpstore.CODE_TTL_SECONDS // 60,
        )
        sent = telegram.send_message(account.telegram_id, text, parse_mode="HTML")
        if not sent:
            return _error(
                "telegram_send_failed",
                "Kodni Telegram'ga yuborib bo'lmadi. Botni ochib, qaytadan "
                "urinib ko'ring.",
                http_status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {"expires_in": otpstore.CODE_TTL_SECONDS}, status=status.HTTP_200_OK
        )


@extend_schema(tags=["auth"])
class VerifyCodeView(APIView):
    """Kodni tekshiradi; to'g'ri bo'lsa reset qadami uchun token beradi."""

    permission_classes = [permissions.AllowAny]
    serializer_class = VerifyCodeSerializer

    def post(self, request):
        serializer = VerifyCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone"]
        purpose = serializer.validated_data["purpose"]
        code = serializer.validated_data["code"]

        result, token = otpstore.verify_code(purpose, phone, code)
        if result == otpstore.VerifyResult.OK:
            return Response({"token": token}, status=status.HTTP_200_OK)
        if result == otpstore.VerifyResult.EXPIRED:
            return _error("expired", "Kod muddati tugadi. Yangi kod so'rang.")
        if result == otpstore.VerifyResult.TOO_MANY:
            return _error("too_many", "Juda ko'p urinish. Yangi kod so'rang.")
        return _error("invalid", "Kod noto'g'ri. Qaytadan urinib ko'ring.")


@extend_schema(tags=["auth"])
class ResetPasswordView(APIView):
    """Tasdiqlangan token bilan yangi parol o'rnatadi (parolni tiklash)."""

    permission_classes = [permissions.AllowAny]
    serializer_class = ResetPasswordSerializer

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone"]
        token = serializer.validated_data["token"]
        password = serializer.validated_data["password"]

        # Bir martalik tokenni Redis'dan tekshirib, darhol ishlatamiz.
        if not otpstore.consume_token(token, phone, "reset"):
            return _error(
                "invalid_token",
                "Token yaroqsiz yoki muddati tugagan. Qaytadan boshlang.",
            )

        with transaction.atomic():
            user = User.objects.select_for_update().filter(phone=phone).first()
            if user is None:
                return _error(
                    "no_user",
                    "Bu raqam bilan foydalanuvchi topilmadi.",
                    http_status=status.HTTP_404_NOT_FOUND,
                )

            try:
                validate_password(password, user=user)
            except DjangoValidationError as exc:
                return _error("weak_password", exc.messages[0])

            user.set_password(password)
            user.save(update_fields=["password"])

        return Response(status=status.HTTP_204_NO_CONTENT)
