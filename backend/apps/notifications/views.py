from django.db.models import Exists, OuterRef, Q
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.lang import LangSerializerContextMixin
from .models import Notification, NotificationRead, PushDevice
from .serializers import (
    NotificationSerializer,
    PushDeviceSerializer,
    PushTokenSerializer,
    UnreadCountSerializer,
)


def visible_to(user):
    """Hammaga yuborilganlar va shu foydalanuvchi tanlanganlar ichida bo'lganlari."""
    return Notification.objects.filter(is_active=True).filter(
        Q(audience=Notification.Audience.ALL) | Q(recipients=user)
    ).distinct()


def with_read_flag(qs, user):
    read = NotificationRead.objects.filter(notification=OuterRef("pk"), user=user)
    return qs.annotate(is_read=Exists(read))


@extend_schema(tags=["notifications"], description="Bildirishnomalar ro'yxati.")
class NotificationListView(LangSerializerContextMixin, generics.ListAPIView):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        qs = with_read_flag(visible_to(self.request.user), self.request.user)
        if self.request.query_params.get("unread") in ("1", "true"):
            qs = qs.filter(is_read=False)
        return qs


@extend_schema(
    tags=["notifications"],
    responses=UnreadCountSerializer,
    description="Profil ekranidagi qizil badge uchun o'qilmaganlar soni.",
)
class UnreadCountView(APIView):
    def get(self, request):
        count = with_read_flag(visible_to(request.user), request.user).filter(
            is_read=False
        ).count()
        return Response({"unread": count})


@extend_schema(tags=["notifications"], description="Bitta bildirishnomani o'qildi deb belgilash.")
class MarkReadView(APIView):
    def post(self, request, pk: int):
        notification = visible_to(request.user).filter(pk=pk).first()
        if notification is None:
            return Response({"detail": "Topilmadi."}, status=status.HTTP_404_NOT_FOUND)
        NotificationRead.objects.get_or_create(notification=notification, user=request.user)
        return Response({"detail": "O'qildi deb belgilandi."})


@extend_schema(tags=["notifications"], description="Barchasini o'qildi deb belgilash.")
class MarkAllReadView(APIView):
    def post(self, request):
        # Materialise before inserting — the queryset would come back empty
        # once the NotificationRead rows exist.
        unread = list(
            with_read_flag(visible_to(request.user), request.user).filter(is_read=False)
        )
        NotificationRead.objects.bulk_create(
            [NotificationRead(notification=n, user=request.user) for n in unread],
            ignore_conflicts=True,
        )
        return Response({"detail": "Barchasi o'qildi deb belgilandi.", "marked": len(unread)})


@extend_schema(
    tags=["notifications"],
    request=PushDeviceSerializer,
    description="Telefonning FCM tokenini ro'yxatdan o'tkazish (mehmon ham). "
    "Token boshqa hisobda bo'lsa joriy foydalanuvchiga o'tadi.",
)
class PushDeviceRegisterView(APIView):
    def post(self, request):
        serializer = PushDeviceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        PushDevice.objects.update_or_create(
            token=data["token"],
            defaults={
                "user": request.user,
                "platform": data["platform"],
                "app_version": data["app_version"],
                "is_active": True,
                "last_error": "",
            },
        )
        return Response({"detail": "Qurilma ro'yxatdan o'tdi."})


@extend_schema(
    tags=["notifications"],
    request=PushTokenSerializer,
    description="Chiqishdan oldin: shu telefonga bu hisob xabarlari kelmasin.",
)
class PushDeviceRemoveView(APIView):
    def post(self, request):
        serializer = PushTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        PushDevice.objects.filter(user=request.user, token=serializer.validated_data["token"]).delete()
        return Response({"detail": "Qurilma o'chirildi."})
