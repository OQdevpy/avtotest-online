"""PRO to'lovlari admin'i.

Payme/Click kalitlarini faqat superuser ko'radi va o'zgartiradi. Kalit maydoni
sahifaga hech qachon qaytarib chiqarilmaydi: bo'sh qoldirilsa eski qiymat saqlanadi.
Buyurtma va tranzaksiyalar faqat o'qish uchun — ularni webhook'lar o'zgartiradi.
"""

from django.utils.html import format_html
from django import forms
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse

from .models import PaymentConfig, ProOrder, ProPlan, ProviderTransaction

SECRET_FIELDS = (
    ("payme_secret_key", "Payme kaliti"),
    ("payme_test_secret_key", "Payme test kaliti"),
    ("click_secret_key", "Click kaliti"),
)


class ProPlanForm(forms.ModelForm):
    class Meta:
        model = ProPlan
        fields = "__all__"
        widgets = {"color": forms.TextInput(attrs={"type": "color", "style": "width:80px;height:36px"})}


@admin.register(ProPlan)
class ProPlanAdmin(admin.ModelAdmin):
    form = ProPlanForm
    list_display = ("title_uz", "days", "price", "swatch", "order", "is_active")
    list_editable = ("days", "price", "order", "is_active")
    list_display_links = ("title_uz",)

    @admin.display(description="Rang")
    def swatch(self, obj):
        return format_html(
            '<span style="display:inline-block;width:22px;height:22px;border-radius:50%;'
            'border:3px solid {};vertical-align:middle"></span> {}', obj.color, obj.color)


class PaymentConfigForm(forms.ModelForm):
    payme_secret_key = forms.CharField(
        label="Payme kaliti", required=False,
        widget=forms.PasswordInput(render_value=False))
    payme_test_secret_key = forms.CharField(
        label="Payme test kaliti", required=False,
        widget=forms.PasswordInput(render_value=False))
    click_secret_key = forms.CharField(
        label="Click kaliti", required=False,
        widget=forms.PasswordInput(render_value=False))

    class Meta:
        model = PaymentConfig
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, _ in SECRET_FIELDS:
            is_set = bool(self.instance.pk and getattr(self.instance, name))
            state = "o'rnatilgan" if is_set else "o'rnatilmagan"
            self.fields[name].help_text = (
                f"Hozir: {state}. Bo'sh qoldirilsa o'zgarmaydi.")

    def save(self, commit=True):
        obj = super().save(commit=False)
        for name, _ in SECRET_FIELDS:
            value = (self.cleaned_data.get(name) or "").strip()
            if value:
                setattr(obj, name, value)
        if commit:
            obj.save()
        return obj


@admin.register(PaymentConfig)
class PaymentConfigAdmin(admin.ModelAdmin):
    form = PaymentConfigForm
    fieldsets = (
        ("Sotish", {"fields": ("sell_android", "sell_ios")}),
        ("Payme", {"fields": ("payme_enabled", "payme_test_mode", "payme_merchant_id",
                              "payme_secret_key", "payme_test_secret_key",
                              "payme_allowed_ips")}),
        ("Click", {"fields": ("click_enabled", "click_service_id", "click_merchant_id",
                              "click_merchant_user_id", "click_secret_key")}),
        ("Fiskal chek (ixtiyoriy)", {"fields": ("mxik_code", "package_code",
                                                "vat_percent")}),
    )

    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        if not self.has_view_permission(request):
            return super().changelist_view(request, extra_context)
        PaymentConfig.get()
        return redirect(reverse("admin:payments_paymentconfig_change", args=(1,)))

    def change_view(self, request, object_id, form_url="", extra_context=None):
        if str(object_id) == "1" and self.has_change_permission(request):
            PaymentConfig.get()
        return super().change_view(request, object_id, form_url, extra_context)


class ProviderTransactionInline(admin.TabularInline):
    model = ProviderTransaction
    extra = 0
    can_delete = False
    fields = ("provider", "external_id", "state", "amount", "create_time",
              "perform_time", "cancel_time", "reason", "extra")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ProOrder)
class ProOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "days", "amount", "provider", "status",
                    "created_at", "paid_at")
    list_filter = ("status", "provider")
    search_fields = ("user__phone", "id")
    list_select_related = ("user",)
    inlines = (ProviderTransactionInline,)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
