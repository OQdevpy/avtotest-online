from datetime import timedelta

from django.contrib import admin, messages
from django.db.models import Count
from django.utils import timezone

from apps.accounts.models import Device
from .models import AppRelease, UserAppVersion

ACTIVE_DAYS = 30


@admin.register(AppRelease)
class AppReleaseAdmin(admin.ModelAdmin):
    list_display = ("platform", "min_version", "latest_version", "review_mode", "store_url", "updated_at")
    # Tekshiruv rejimini ro'yxatning o'zidan bir bosishda yoqish/o'chirish
    list_editable = ("review_mode",)


@admin.register(UserAppVersion)
class UserAppVersionAdmin(admin.ModelAdmin):
    list_display = ("user", "platform", "version", "last_seen")
    list_filter = ("platform", "version")
    search_fields = ("user__phone", "user__full_name")
    list_select_related = ("user",)
    readonly_fields = ("user", "platform", "version", "last_seen")

    def has_add_permission(self, request):
        return False

    def changelist_view(self, request, extra_context=None):
        # Sahifa tepasida: oxirgi 30 kunda qaysi versiyada nechta faol foydalanuvchi.
        since = timezone.now() - timedelta(days=ACTIVE_DAYS)
        rows = (UserAppVersion.objects.filter(last_seen__gte=since)
                .values("platform", "version").annotate(n=Count("pk"))
                .order_by("platform", "-version"))
        summary = ", ".join(f"{r['platform']} {r['version']}: {r['n']}" for r in rows) or "hali yo'q"
        old = (Device.objects.filter(platform=Device.Platform.MOBILE, last_seen__gte=since)
               .exclude(user__app_version__last_seen__gte=since)
               .values("user").distinct().count())
        messages.info(request, f"Oxirgi {ACTIVE_DAYS} kunda faol — {summary}. "
                               f"Versiya yubormaydigan eski ilovada: {old}.")
        return super().changelist_view(request, extra_context)
