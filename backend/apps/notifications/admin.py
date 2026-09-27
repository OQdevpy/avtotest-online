from django.contrib import admin

from .models import Notification, NotificationRead


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title_uz", "kind", "audience", "is_active", "created_at")
    list_filter = ("kind", "is_active")
    search_fields = ("title_uz", "title_ru", "title_cry", "body_uz")
    fieldsets = (
        (None, {"fields": ("kind", "is_active", "user")}),
        ("Sarlavha", {"fields": ("title_uz", "title_ru", "title_cry")}),
        ("Matn", {"fields": ("body_uz", "body_ru", "body_cry")}),
    )

    @admin.display(description="Kimga")
    def audience(self, obj):
        return "Hammaga" if obj.is_broadcast else str(obj.user)


@admin.register(NotificationRead)
class NotificationReadAdmin(admin.ModelAdmin):
    list_display = ("user", "notification", "read_at")
    search_fields = ("user__phone",)
    list_select_related = ("user", "notification")
