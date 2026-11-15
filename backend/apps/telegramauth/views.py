"""Telegram orqali kirish.

Oqim:
    1) POST /api/v1/auth/telegram/start/          {lang}  -> {token, link, expires_in}
    2) foydalanuvchi botda kontaktini yuboradi (raqam va ism sessiyaga yoziladi)
    3) GET  /api/v1/auth/telegram/status/<token>/          -> {status}
    4) POST /api/v1/auth/telegram/claim/  {token, guest_refresh?, platform?, device_label?}
                                                           -> {user, tokens, created}

Sessiyalar Redis'da (TTL bilan) — ``verification`` moduliga qarang.
"""

from __future__ import annotations

from django.conf import settings
from django.db import transaction
from django.shortcuts import render
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.net import client_ip

from . import claim, verification
from .serializers import TelegramClaimSerializer, TelegramStartSerializer


def _error(code: str, detail: str, http_status: int = status.HTTP_400_BAD_REQUEST):
    """Frontend `code` bo'yicha shoxlanadi; `detail` — o'qiladigan matn."""
    return Response({"code": code, "detail": detail}, status=http_status)


@extend_schema(tags=["auth"])
class TelegramStartView(APIView):
    """Telegram orqali kirish sessiyasini ochadi (raqamsiz).

    Ilova `link` ni ochadi; bot kontaktdan raqam va ismni sessiyaga yozadi,
    ilova holatni `telegram/status/<token>/` dan so'raydi va tasdiqlangach
    `telegram/claim/` bilan tokenlarni oladi.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = ()
    serializer_class = TelegramStartSerializer

    def post(self, request):
        from apps.accounts.views import UPDATE_REQUIRED

        # Eski ilova raqam bilan `register`/`reset` sessiyasini so'raydi — u yangilanishi kerak.
        if request.data.get("purpose", "auth") != "auth":
            return Response(UPDATE_REQUIRED, status=status.HTTP_400_BAD_REQUEST)
        serializer = TelegramStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            token = verification.start_session(
                None, serializer.validated_data["purpose"],
                serializer.validated_data["lang"], ip=client_ip(request),
            )
        except verification.TooManySessions:
            return _error("too_many", "Juda ko'p urinish. Birozdan so'ng qayta urinib ko'ring.",
                          http_status=status.HTTP_429_TOO_MANY_REQUESTS)
        return Response({"token": token, "link": verification.bot_link(token),
                         "expires_in": verification.SESSION_TTL})


@extend_schema(tags=["auth"])
class TelegramClaimView(APIView):
    """Tasdiqlangan sessiyani tokenlarga almashtiradi (bir marta).

    Raqam bazada bo'lsa — kirish (`200`), bo'lmasa — yangi o'quvchi (`201`);
    `guest_refresh` berilsa mehmon hisobi natijalari bilan aylanadi.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = ()
    serializer_class = TelegramClaimSerializer

    def post(self, request):
        from apps.accounts.devices import DeviceLimitReached
        from apps.accounts.serializers import UserSerializer, issue_tokens
        from apps.accounts.views import DEVICE_LIMIT_MESSAGE, VERIFICATION_INVALID

        serializer = TelegramClaimSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        session = verification.consume_auth(data["token"])
        if session is None:
            return Response(VERIFICATION_INVALID, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            user, created = claim.user_for_phone(
                session["phone"], session.get("full_name") or "",
                session.get("lang") or "uz", data.get("guest_refresh", ""),
            )
            if claim.is_blocked(user):
                return _error("blocked", "Hisob bloklangan.", status.HTTP_403_FORBIDDEN)
            try:
                tokens = issue_tokens(user, platform=data.get("platform", ""),
                                      label=data.get("device_label", ""))
            except DeviceLimitReached:
                return Response({"detail": DEVICE_LIMIT_MESSAGE},
                                status=status.HTTP_403_FORBIDDEN)
        return Response(
            {"user": UserSerializer(user).data, "tokens": tokens, "created": created},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


@extend_schema(tags=["auth"])
class TelegramStatusView(APIView):
    """Tasdiqlash holati: pending | verified | mismatch | expired."""

    permission_classes = [permissions.AllowAny]

    def get(self, request, token: str):
        return Response({"status": verification.status_of(token)})


@extend_schema(exclude=True)
class AppReturnView(APIView):
    """Botdagi «Ilovaga qaytish» tugmasi ochadigan sahifa — mobil ilovani ochadi.

    Telegram inline tugmalari faqat http(s)/tg havolalarini qabul qiladi, shuning
    uchun ilova sxemasiga shu https sahifa orqali o'tiladi. Sahifada hech qanday
    ma'lumot yo'q — havola ochiq.
    """

    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()

    def get(self, request):
        scheme, package = settings.APP_SCHEME, settings.APP_ANDROID_PACKAGE
        return render(request, "telegramauth/app_return.html", {
            "scheme_url": f"{scheme}://open",
            "intent_url": f"intent://open#Intent;scheme={scheme};package={package};end",
        })
