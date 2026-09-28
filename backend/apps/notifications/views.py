from django.db.models import Exists, OuterRef, Q
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.lang import LangSerializerContextMixin
from .models import Notification, NotificationRead
from .serializers import NotificationSerializer, UnreadCountSerializer


def visible_to(user):
    """Broadcast notifications plus the ones targeted at this user."""
    return Notification.objects.filter(is_active=True).filter(
        Q(user__isnull=True) | Q(user=user)
    )


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
