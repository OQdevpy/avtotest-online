from django.contrib import admin

from .models import TelegramAccount


@admin.register(TelegramAccount)
class TelegramAccountAdmin(admin.ModelAdmin):
    list_display = ("telegram_id", "phone", "language", "user", "verified_at", "created_at")
    list_filter = ("language",)
    search_fields = ("telegram_id", "phone", "username", "full_name", "user__phone")
    raw_id_fields = ("user",)
