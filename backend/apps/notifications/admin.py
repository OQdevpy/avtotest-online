from django.contrib import admin

from .models import Notification, NotificationRead, PushDevice


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title_uz", "kind", "audience", "is_active", "created_at")
    list_filter = ("kind", "is_active")
    search_fields = ("title_uz", "title_ru", "title_cry", "body_uz")
    autocomplete_fields = ("recipients",)
    fieldsets = (
        (None, {"fields": ("kind", "is_active", "audience", "recipients")}),
        ("Sarlavha", {"fields": ("title_uz", "title_ru", "title_cry")}),
        ("Matn", {"fields": ("body_uz", "body_ru", "body_cry")}),
    )

    @admin.display(description="Kimga")
    def audience(self, obj):
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
