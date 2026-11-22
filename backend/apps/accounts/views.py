from django.db import transaction
from django.http import Http404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from .models import AccessCode, User, guest_phone
from .serializers import (
    AccessCodeLoginSerializer,
    AccessCodeSerializer,
    GuestSerializer,
    DeviceSerializer,
    UserSerializer,
    issue_tokens,
)
from common.authentication import GUEST_EXPIRED
from common.permissions import IsAdminRole
from rest_framework.throttling import ScopedRateThrottle

from .devices import (
    device_for_refresh,
    grandfather_device,
    rotate,
)
from .models import Device


DEVICE_LIMIT_MESSAGE = "Ushbu hisob allaqachon boshqa qurilmada ochiq."
OTHER_COMPUTER_MESSAGE = ("Bu kod boshqa kompyuterga biriktirilgan. "
                          "Yangi kompyuter uchun shefga murojaat qiling.")
OUTDATED_CLIENT_MESSAGE = "Ilovaning yangi versiyasini o'rnating."
MIN_DEVICE_ID = 16
UPDATE_REQUIRED = {"code": "update_required", "detail": "Ilovaning yangi versiyasini o'rnating."}
VERIFICATION_INVALID = {"code": "verification_invalid",
                        "detail": "Raqam tasdig'i yaroqsiz yoki muddati o'tgan. Qaytadan tasdiqlang."}


@extend_schema(tags=["auth"], deprecated=True)
class UpdateRequiredView(APIView):
    """Yopilgan yo'l: parol, ijtimoiy kirish va OTP. Kirish faqat Telegram orqali
    (`auth/telegram/`); eski ilova `update_required` ni ko'rib yangilanadi."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = ()

    def post(self, request, *args, **kwargs):
        return Response(UPDATE_REQUIRED, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["auth"])
class ReviewLoginView(APIView):
    """Do'kon tekshiruvchisi uchun telefon + parol bilan kirish.

    Faqat `review_account=True` hisob kiradi. Boshqa har qanday holatda (oddiy
    foydalanuvchi, noto'g'ri parol) eski ilovaga ham tanish `update_required`
    qaytadi — kirish faqat Telegram orqali, test hisobi borligi sezilmaydi.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = ()
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "review_login"

    def post(self, request):
        from django.contrib.auth import authenticate
        from django.core.exceptions import ValidationError as DjangoValidationError

        from .serializers import issue_tokens, normalize_phone

        try:
            phone = normalize_phone(str(request.data.get("phone", "")))
        except DjangoValidationError:
            phone = ""
        password = str(request.data.get("password", ""))
        user = authenticate(request, username=phone, password=password) if phone and password else None
        if user is None or not user.is_active or not user.review_account:
            return Response(UPDATE_REQUIRED, status=status.HTTP_400_BAD_REQUEST)
        tokens = issue_tokens(user, platform=str(request.data.get("platform", "")),
                              label="App Review")
        return Response({"user": UserSerializer(user).data, "tokens": tokens})


@extend_schema(tags=["auth"])
class GuestView(generics.GenericAPIView):
    """Mehmon sessiyasi — ilova birinchi ochilganda, ro'yxatdan o'tmasdan.

    Telefonsiz `role=guest` foydalanuvchi va `settings.GUEST_DAYS` kunlik
    sessiya. Muddat tugagach har so'rov `401 guest_expired` oladi.
    """

    serializer_class = GuestSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "guest"

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        with transaction.atomic():
            # `create_user` emas — u telefonni `+998` ga normallashtiradi.
            user = User(phone=guest_phone(), role=User.Role.GUEST, language=data["lang"])
            user.set_unusable_password()
            user.save()
            tokens = issue_tokens(user, label=data.get("device_label", ""),
                                  machine_id=data["device_id"], guest=True)
        device = user.devices.get()
        return Response(
            {"user": UserSerializer(user).data, "tokens": tokens,
             "guest_until": device.expires_at.isoformat()},
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["auth"])
class MeView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    def perform_destroy(self, instance):
        # Hisob va unga bog'liq barcha ma'lumotlar (progress, xatolar, saqlangan
        # savollar, natijalar) FK cascade orqali o'chadi. Apple/Google talabi.
        instance.delete()


@extend_schema(tags=["auth"])
class LogoutView(APIView):
    """Joriy sessiyani yopadi — qurilma slotini bo'shatadi."""

    def post(self, request):
        token = request.data.get("refresh")
        jti = None
        if token:
            try:
                jti = RefreshToken(token)["jti"]
            except TokenError:
                jti = None
        queryset = Device.objects.filter(user=request.user, is_active=True)
        if jti:
            queryset = queryset.filter(refresh_jti=jti)
        queryset.update(is_active=False)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["auth"])
class DeviceListView(generics.ListAPIView):
    """Foydalanuvchining faol sessiyalari."""

    serializer_class = DeviceSerializer

    def get_queryset(self):
        return Device.objects.filter(user=self.request.user, is_active=True)


@extend_schema(tags=["auth"])
class DeviceDeleteView(APIView):
    """Bitta sessiyani uzadi. Boshqa foydalanuvchinikiga tegib bo'lmaydi."""

    def delete(self, request, pk: int):
        device = Device.objects.filter(
            pk=pk, user=request.user, is_active=True
        ).first()
        if device is None:
            raise Http404
        Device.objects.filter(pk=device.pk).update(is_active=False)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["auth"])
class DeviceAwareTokenRefreshView(TokenRefreshView):
    """Refresh — faqat qurilma sessiyasi tirik bo'lsa.

    Muddati o'tgan yoki uzilgan qurilma bilan token yangilanmaydi: web va
    desktopda sotilgan 12 kunlik kirish cheksiz aylanib ketmaydi.
    """

    def post(self, request, *args, **kwargs):
        raw = request.data.get("refresh")
        try:
            incoming = RefreshToken(raw)
        except TokenError:
            return Response({"detail": "Token yaroqsiz."},
                            status=status.HTTP_401_UNAUTHORIZED)

        device, reason = device_for_refresh(incoming["jti"])
        if device is None and reason == "unknown":
            # Bu sessiya `Device` jadvalidan oldin ochilgan (baza eski mobil
            # backupdan tiklangan). Uni chiqarib tashlamaymiz — yozuvni
            # to'ldiramiz. Muddati o'tgan yoki uzilgan qurilma esa quyida rad
            # etiladi, ya'ni 12 kunlik qoida kuchida qoladi.
            device = grandfather_device(incoming)
        if device is None:
            closed = Device.objects.select_related("user").filter(
                refresh_jti=incoming["jti"]).first()
            if closed is not None and closed.user.is_guest:
                # Access token 1 kunda eskiradi — mehmon buni refresh'da bilishi kerak,
                # aks holda ilova tokenni o'chirib, natijalar bilan aylanish imkoni yo'qoladi.
                return Response(GUEST_EXPIRED, status=status.HTTP_401_UNAUTHORIZED)
            return Response({"detail": "Sessiya tugagan yoki uzilgan."},
                            status=status.HTTP_401_UNAUTHORIZED)

        response = super().post(request, *args, **kwargs)
        # ROTATE_REFRESH_TOKENS yoqilgan — yangi jti shu qurilmaga bog'lanadi.
        new_refresh = response.data.get("refresh") if response.status_code == 200 else None
        if new_refresh:
            rotate(device, RefreshToken(new_refresh))
        return response


@extend_schema(tags=["auth"])
class AccessCodeLoginView(generics.GenericAPIView):
    """Shef bergan kod bilan kirish. Kod muddatsiz, lekin bitta kompyuterga.

    Birinchi kirish kodni shu kompyuterga biriktiradi; shu kompyuterdan qayta
    kirish mumkin, boshqasi rad etiladi. Shef `unbind` bilan bo'shatadi.
    """

    serializer_class = AccessCodeLoginSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({"detail": "Kod yaroqsiz yoki muddati tugagan."},
                            status=status.HTTP_401_UNAUTHORIZED)

        code = serializer.context["access_code"]
        data = serializer.validated_data

        # Kod bilan kirish faqat desktop/web sessiyasi — `mobile` deb yozilmaydi.
        requested = (data.get("platform") or "").strip().lower()
        platform = requested if requested in ("desktop", "web") else "desktop"

        machine = (data.get("device_id") or "").strip().lower()
        if len(machine) < MIN_DEVICE_ID:
            # Eski desktop ID yubormaydi — uni qo'yib yuborish qoidani chetlab o'tardi.
            return Response({"detail": OUTDATED_CLIENT_MESSAGE},
                            status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # Qulf: bir vaqtda ikki kompyuterdan kirilsa faqat bittasi biriktiriladi.
            code = AccessCode.objects.select_for_update().get(pk=code.pk)
            if code.device_id and code.device_id != machine:
                return Response({"detail": OTHER_COMPUTER_MESSAGE},
                                status=status.HTTP_403_FORBIDDEN)
            if not code.device_id:
                code.device_id = machine
                code.bound_at = timezone.now()
                code.save(update_fields=["device_id", "bound_at"])
                # Ko'p martalik davrida noma'lum kompyuterlarda ochilgan sessiyalar
                # (machine_id'siz) yopiladi; mobil ilova sessiyasiga tegilmaydi.
                Device.objects.filter(
                    user=code.user, machine_id="", is_active=True,
                    platform__in=(Device.Platform.DESKTOP, Device.Platform.WEB),
                ).update(is_active=False)

            # Sessiya muddatsiz (shef kodni o'chirmaguncha yoki bo'shatmaguncha).
            tokens = issue_tokens(
                code.user,
                platform=platform,
                label=data.get("device_label", ""),
                unlimited=True,
                machine_id=machine,
            )
        return Response({"user": UserSerializer(code.user).data, "tokens": tokens})


@extend_schema(tags=["manage"])
class ManageAccessCodeViewSet(viewsets.ModelViewSet):
    """Shef uchun kirish kodlari."""

    serializer_class = AccessCodeSerializer
    permission_classes = [IsAdminRole]
    queryset = AccessCode.objects.select_related("user", "created_by")

    def perform_create(self, serializer):
        serializer.instance = AccessCode.generate(
            user=serializer.validated_data["user"],
            created_by=self.request.user,
            valid_days=serializer.validated_data.get("valid_days"),
        )

    @action(detail=True, methods=["post"])
    def unbind(self, request, pk=None):
        """Kompyuter bog'lanishini bekor qiladi — o'quvchi yangi kompyuterdan kira oladi."""
        code = self.get_object()
        code.unbind()
        return Response(self.get_serializer(code).data)

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        code = self.get_object()
        code.revoke()
        return Response(self.get_serializer(code).data)

    def perform_update(self, serializer):
        # `is_active=False` PATCH bilan berilsa ham ochiq kompyuter to'xtasin
        code = serializer.save()
        if not code.is_active:
            code.close_sessions()
