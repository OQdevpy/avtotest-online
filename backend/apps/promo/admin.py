from django.contrib import admin
from django.utils.html import format_html

from .models import Slide


@admin.register(Slide)
class SlideAdmin(admin.ModelAdmin):
    list_display = ("preview", "title", "action", "audience", "order", "is_active",
                    "starts_at", "ends_at")
    list_display_links = ("preview", "title")
    list_editable = ("order", "is_active")
    list_filter = ("is_active", "audience", "action")
    search_fields = ("title",)
    readonly_fields = ("preview_large",)
    fieldsets = (
        (None, {"fields": ("title", "is_active", "order", "audience")}),
        ("Rasm", {"fields": ("image_uz", "image_ru", "image_cry", "preview_large")}),
        ("Bosilganda", {"fields": ("action", "url")}),
        ("Ko'rinish muddati (ixtiyoriy)", {"fields": ("starts_at", "ends_at")}),
    )

    @admin.display(description="Rasm")
    def preview(self, obj):
        if not obj.image_uz:
            return "—"
        return format_html('<img src="{}" style="height:48px;border-radius:6px">', obj.image_uz.url)

    @admin.display(description="Ko'rinishi")
    def preview_large(self, obj):
        if not obj.pk or not obj.image_uz:
            return "Saqlangandan keyin ko'rinadi."
        return format_html('<img src="{}" style="max-width:480px;border-radius:12px">',
                           obj.image_uz.url)
