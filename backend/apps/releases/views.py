from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import APIException
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AppRelease, Platform, UserAppVersion, parse_version


def _current_user(request):
    """Token bo'lsa — foydalanuvchi; eskirgan/yaroqsiz token ham tekshiruvni to'xtatmaydi."""
    try:
        user = request.user
    except APIException:
        return None
    return user if user is not None and user.is_authenticated else None


@extend_schema(
    tags=["app"],
    parameters=[
        OpenApiParameter("platform", description="android | ios", required=True, type=str),
        OpenApiParameter("version", description="Ilova versiyasi, masalan 1.2.0", type=str),
    ],
    description="Ilova ishga tushganda chaqiriladi: majburiy yangilash kerakmi. "
                "Kirgan foydalanuvchining versiyasi statistika uchun yoziladi.",
)
class AppVersionView(APIView):
    permission_classes = (AllowAny,)

    def perform_authentication(self, request):
        # Token faqat statistika uchun — eskirgan token 401 bermasin (`_current_user`).
        pass

    def get(self, request):
        platform = (request.query_params.get("platform") or "").lower()
        if platform not in Platform.values:
            return Response({"detail": "platform: android yoki ios."}, status=400)
        version = (request.query_params.get("version") or "").strip()
        current = parse_version(version)

        release = AppRelease.objects.filter(platform=platform).first() or AppRelease(platform=platform)
        minimum, latest = parse_version(release.min_version), parse_version(release.latest_version)

        user = _current_user(request)
        if user is not None and current is not None:
            UserAppVersion.objects.update_or_create(
                user=user, defaults={"platform": platform, "version": version},
            )

        return Response({
            "platform": platform,
            "version": version,
            "min_version": release.min_version,
            "latest_version": release.latest_version,
            "store_url": release.resolved_store_url,
            # Versiyani yubormagan yoki noto'g'ri yuborgan ilova bloklanmaydi.
            "update_required": bool(current and minimum and current < minimum),
            "update_available": bool(current and latest and current < latest),
        })
