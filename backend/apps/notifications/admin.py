from django.contrib import admin

from .models import Notification, NotificationRead


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
