from datetime import timedelta

from django.contrib import admin, messages
from django.db.models import Count
from django.utils import timezone

from apps.accounts.models import Device
from django import forms

from .models import AppRelease, AppSettings, Section, UserAppVersion

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


class AppSettingsForm(forms.ModelForm):
    locked_sections = forms.MultipleChoiceField(
        label="PRO'siz yopiq bo'limlar", choices=Section.choices, required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Belgilangan bo'limlar PRO'siz foydalanuvchiga qulf bilan ko'rinadi.",
    )

    class Meta:
        model = AppSettings
        fields = ("guest_days", "welcome_pro_days", "paywall_after_signup", "locked_sections")


def conversion_stats(days: int) -> dict:
    """So'nggi `days` kunda kelganlar: mehmon → Telegram → to'lov."""
    from django.db.models import Q

    from apps.accounts.models import User
    from apps.payments.models import ProOrder

    since = timezone.now() - timedelta(days=days)
    joined = User.objects.filter(date_joined__gte=since)
    guests = joined.filter(Q(role=User.Role.GUEST) | Q(guest_converted_at__isnull=False)).count()
    converted_ids = list(joined.filter(guest_converted_at__isnull=False).values_list("pk", flat=True))
    direct = joined.filter(role=User.Role.STUDENT, guest_converted_at__isnull=True).count()
    paid = (ProOrder.objects.filter(user_id__in=converted_ids, status=ProOrder.Status.PAID)
            .values("user_id").distinct().count())
    converted = len(converted_ids)
    return {"guests": guests, "converted": converted, "direct": direct, "paid": paid,
            "rate": round(converted * 100 / guests) if guests else 0,
            "paid_rate": round(paid * 100 / converted) if converted else 0}


@admin.register(AppSettings)
class AppSettingsAdmin(admin.ModelAdmin):
    form = AppSettingsForm
    list_display = ("__str__", "guest_days", "welcome_pro_days", "paywall_after_signup", "updated_at")
    readonly_fields = ("conversion",)

    def get_fieldsets(self, request, obj=None):
        return (
            (None, {"fields": ("guest_days", "welcome_pro_days", "paywall_after_signup",
                               "locked_sections")}),
            ("Konversiya", {"fields": ("conversion",)}),
        )

    @admin.display(description="Mehmon → Telegram → to'lov")
    def conversion(self, obj):
        from django.utils.html import format_html, format_html_join

        rows = []
        for days in (1, 7, 30):
            st = conversion_stats(days)
            rows.append((f"So'nggi {days} kun", st["guests"], st["converted"], st["rate"],
                         st["paid"], st["paid_rate"], st["direct"]))
        body = format_html_join("", "<tr><td>{}</td><td>{}</td><td>{} ({}%)</td><td>{} ({}%)</td><td>{}</td></tr>", rows)
        return format_html(
            '<table style="border-collapse:collapse"><thead><tr>'
            "<th>Davr</th><th>Mehmon bo'lib kirgan</th><th>Telegram'dan o'tgan</th>"
            "<th>Ulardan to'lagan</th><th>To'g'ridan-to'g'ri ro'yxat</th></tr></thead>"
            "<tbody>{}</tbody></table>"
            '<p style="margin-top:8px">Mehmondan o\'tganlar ro\'yxati: Foydalanuvchilar → '
            "«Mehmondan o'tganmi» filtri.</p>", body)

    def has_add_permission(self, request):
        return not AppSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
