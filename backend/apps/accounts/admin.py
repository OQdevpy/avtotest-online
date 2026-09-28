from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import AccessCode, Device, SocialAccount, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("-date_joined",)
    list_display = ("phone", "full_name", "role", "branch", "hujjat",
                    "is_pro", "is_active", "date_joined")
    list_filter = ("role", "branch", "is_active", "is_staff", "is_pro", "hujjat", "language")
    search_fields = ("phone", "full_name")
    list_select_related = ("branch",)
    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("Profil", {"fields": ("full_name", "language", "dark_theme")}),
        # Rol biznes huquqini belgilaydi; `is_staff` faqat admin paneliga kirishni.
        ("Rol va filial", {"fields": ("role", "branch", "hujjat")}),
        ("PRO", {"fields": ("is_pro", "pro_until")}),
        ("Sessiya", {"fields": ("max_devices",),
                     "description": "Bo'sh qoldirilsa platforma bo'yicha "
                                    "standart limit amal qiladi."}),
        ("Ruxsatlar", {"fields": ("is_active", "is_staff", "is_superuser",
                                  "groups", "user_permissions")}),
        ("Sanalar", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",),
                "fields": ("phone", "password1", "password2", "full_name",
                           "role", "branch")}),
    )


@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = ("provider", "uid", "user", "created_at")
    list_filter = ("provider",)
    search_fields = ("uid", "email", "user__phone")


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "platform", "label", "created_at",
                    "expires_at", "is_active")
    list_filter = ("platform", "is_active")
    search_fields = ("user__phone", "user__full_name", "label")
    readonly_fields = ("refresh_jti", "created_at", "last_seen")


@admin.register(AccessCode)
class AccessCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "user", "valid_days", "activated_at",
                    "expires_at", "is_active", "created_by")
    list_filter = ("is_active",)
    search_fields = ("code", "user__phone", "user__full_name")
    readonly_fields = ("code", "activated_at", "expires_at", "created_at")
    autocomplete_fields = ("user", "created_by")

    def save_model(self, request, obj, form, change):
        # `code` faqat o'qish uchun — yangi yozuvga kodni shu yerda beramiz,
        # aks holda bo'sh kod saqlanib, ikkinchisi unique xatosiga tushardi.
        if not obj.code:
            obj.code = AccessCode.new_code()
        if obj.created_by_id is None:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
