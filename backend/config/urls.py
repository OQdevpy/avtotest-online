from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.decorators.cache import cache_control
from django.views.static import serve as serve_static


# Media (rasm/audio) — mijozda uzoq HTTP-kesh (30 kun), qayta so'ralmaydi.
@cache_control(public=True, max_age=60 * 60 * 24 * 30)
def serve_media(request, path):
    return serve_static(request, path, document_root=settings.MEDIA_ROOT)
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from common.views import privacy_policy

api_v1 = [
    path("auth/", include("apps.accounts.urls")),
    path("auth/", include("apps.telegramauth.urls")),
    path("teacher/", include("apps.accounts.teacher_urls")),
    path("manage/", include("apps.accounts.manage_urls")),
    path("manage/", include("apps.content.manage_urls")),
    path("manage/", include("apps.billing.urls")),
    path("", include("apps.content.urls")),
    path("exams/", include("apps.exams.urls")),
    path("progress/", include("apps.progress.urls")),
    path("notifications/", include("apps.notifications.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("privacy/", privacy_policy),   # App Store/Play maxfiylik siyosati
    path("api/v1/", include(api_v1)),
    # OpenAPI
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

# Savol rasmlari. Docker'da oldida nginx bo'lmagani uchun media DEBUG=False
# rejimida ham shu yerdan uzatiladi.
_media_prefix = settings.MEDIA_URL.lstrip("/")
urlpatterns += [
    re_path(rf"^{_media_prefix}(?P<path>.*)$", serve_media),
]
