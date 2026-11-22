from django.contrib import admin, messages
from django.template.response import TemplateResponse
from django.utils.html import format_html

from . import push
from .forms import NotificationAdminForm, SendPushForm
from .models import Notification, NotificationRead, PushDevice

Status = Notification.PushStatus


def can_send(request) -> bool:
    return request.user.has_perm("notifications.add_notification")


def send_notification(modeladmin, request, queryset):
    """Foydalanuvchilar ro'yxatidan: tanlanganlarga xabar (+ push) yuborish."""
    form = SendPushForm(request.POST if request.POST.get("apply") else None)
    if form.is_bound and form.is_valid():
        n = Notification.objects.create(
            audience=Notification.Audience.SELECTED, push_status=Status.PENDING,
            **form.cleaned_data,
        )
        n.recipients.set(queryset)
        count = n.recipients.count()
        modeladmin.message_user(
            request, f"Bildirishnoma {count} kishiga navbatga qo'yildi (#{n.pk}). "
            "Natija Bildirishnomalar bo'limida ko'rinadi.", messages.SUCCESS)
        return None
    select_across = request.POST.get("select_across") == "1"
    return TemplateResponse(request, "admin/notifications/send_push.html", {
        **modeladmin.admin_site.each_context(request),
        "title": "Bildirishnoma yuborish",
        "opts": modeladmin.model._meta,
        "form": form,
        "selected_count": queryset.count(),
        "with_device": queryset.filter(push_devices__is_active=True).distinct().count(),
        "select_across": select_across,
        "selected_pks": [] if select_across else list(queryset.values_list("pk", flat=True)),
        "first_pk": queryset.values_list("pk", flat=True).first(),
        "firebase_ready": push.is_configured(),
    })


send_notification.short_description = "Bildirishnoma yuborish (push)"
send_notification.allowed_permissions = ("notify",)


class HasPushDeviceFilter(admin.SimpleListFilter):
    title = "push qurilma"
    parameter_name = "push"

    def lookups(self, request, model_admin):
        return (("yes", "Bor"), ("no", "Yo'q"))

    def queryset(self, request, queryset):
        active = {"push_devices__is_active": True}
        if self.value() == "yes":
            return queryset.filter(**active).distinct()
        if self.value() == "no":
            return queryset.exclude(**active)
        return queryset


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    form = NotificationAdminForm
    list_display = ("title_uz", "kind", "audience_label", "is_active", "push_info", "created_at")
    list_filter = ("kind", "audience", "is_active", "push_status")
    actions = ("resend_push",)
    readonly_fields = ("push_status", "push_sent", "push_failed", "pushed_at")
    search_fields = ("title_uz", "title_ru", "title_cry", "body_uz")
    autocomplete_fields = ("recipients",)
    fieldsets = (
        (None, {"fields": ("kind", "is_active", "audience", "recipients", "send_push")}),
        ("Sarlavha", {"fields": ("title_uz", "title_ru", "title_cry")}),
        ("Matn", {"fields": ("body_uz", "body_ru", "body_cry"),
                  "description": "Har kimga o'z tilida boradi; bo'sh tillarga o'zbekchasi."}),
        ("Push natijasi", {"fields": ("push_status", "push_sent", "push_failed", "pushed_at")}),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Mavjud xabarni tahrirlashda push qayta ketmasin (buning uchun amal bor)
        form.base_fields["send_push"].initial = obj is None
        return form

    def save_model(self, request, obj, form, change):
        if form.cleaned_data.get("send_push") and obj.push_status != Status.SENDING:
            obj.push_status = Status.PENDING
        super().save_model(request, obj, form, change)

    @admin.display(description="Push")
    def push_info(self, obj):
        if obj.push_status in (Status.DONE, Status.FAILED):
            return format_html("{} · {} ta / xato {}", obj.get_push_status_display(),
                               obj.push_sent, obj.push_failed)
        return obj.get_push_status_display()

    @admin.action(description="Push'ni qayta yuborish")
    def resend_push(self, request, queryset):
        count = queryset.exclude(push_status=Status.SENDING).update(push_status=Status.PENDING)
        self.message_user(request, f"{count} ta xabar push navbatiga qo'yildi.", messages.SUCCESS)

    @admin.display(description="Kimga")
    def audience_label(self, obj):
        if obj.is_broadcast:
            return "Hammaga"
        return f"{obj.recipients.count()} kishi"


@admin.register(NotificationRead)
class NotificationReadAdmin(admin.ModelAdmin):
    list_display = ("user", "notification", "read_at")
    search_fields = ("user__phone",)
    list_select_related = ("user", "notification")


@admin.register(PushDevice)
class PushDeviceAdmin(admin.ModelAdmin):
    """Faqat ko'rish uchun — tokenlarni ilova o'zi yozadi."""

    list_display = ("user", "platform", "app_version", "is_active", "last_error", "updated_at")
    list_filter = ("platform", "is_active")
    search_fields = ("user__phone", "user__full_name", "token")
    list_select_related = ("user",)
    readonly_fields = ("user", "token", "platform", "app_version", "last_error",
                       "created_at", "updated_at")

    def has_add_permission(self, request):
        return False
