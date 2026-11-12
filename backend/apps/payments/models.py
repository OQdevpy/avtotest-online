"""PRO obunani sotish: tariflar, provayder sozlamalari, buyurtma va tranzaksiyalar.

Narx, kunlar, merchant ID va kalitlar faqat shu yerda (admin orqali) — kodda ham,
ilovada ham yo'q. Pul butun so'mda; Payme bilan tiyin faqat webhook chegarasida.
"""

import re

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from . import crypto


class Provider(models.TextChoices):
    PAYME = "payme", "Payme"
    CLICK = "click", "Click"


class ProPlan(models.Model):
    title_uz = models.CharField("Nomi (uz)", max_length=120)
    title_ru = models.CharField("Nomi (ru)", max_length=120, blank=True)
    title_cry = models.CharField("Nomi (kirill)", max_length=120, blank=True)
    days = models.PositiveIntegerField("Kunlar", validators=[MinValueValidator(1)])
    price = models.PositiveIntegerField("Narx (so'm)", validators=[MinValueValidator(1)])
    order = models.PositiveIntegerField("Tartib", default=0, db_index=True)
    is_active = models.BooleanField("Faol", default=True)

    class Meta:
        ordering = ("order", "id")
        verbose_name = "PRO tarif"
        verbose_name_plural = "PRO tariflar"

    def __str__(self) -> str:
        return f"{self.title_uz} — {self.days} kun, {self.price} so'm"


def _secret(field: str):
    """`<field>_enc` ustunini ochiq qiymat sifatida o'qib-yozadigan property."""

    def getter(self) -> str:
        return crypto.decrypt(getattr(self, f"{field}_enc"))

    def setter(self, value: str) -> None:
        setattr(self, f"{field}_enc", crypto.encrypt(value or ""))

    return property(getter, setter)


class PaymentConfig(models.Model):
    """Yagona yozuv (pk=1): qaysi platformada sotiladi va Payme/Click kalitlari."""

    sell_android = models.BooleanField("Android'da sotish", default=True)
    sell_ios = models.BooleanField(
        "iOS'da sotish", default=False,
        help_text="Apple qoidalari (3.1.1) ilova ichida tashqi to'lovni cheklaydi.",
    )

    payme_enabled = models.BooleanField("Payme yoqilgan", default=False)
    payme_test_mode = models.BooleanField("Payme test rejimi", default=False)
    payme_merchant_id = models.CharField("Payme kassa ID", max_length=64, blank=True)
    payme_secret_key_enc = models.TextField(blank=True, editable=False)
    payme_test_secret_key_enc = models.TextField(blank=True, editable=False)
    payme_allowed_ips = models.TextField(
        "Payme IP'lari", blank=True,
        help_text="Vergul yoki yangi qator bilan, CIDR ham bo'ladi. Bo'sh — cheklovsiz.",
    )

    click_enabled = models.BooleanField("Click yoqilgan", default=False)
    click_service_id = models.CharField("Click service ID", max_length=32, blank=True)
    click_merchant_id = models.CharField("Click merchant ID", max_length=32, blank=True)
    click_merchant_user_id = models.CharField("Click merchant user ID", max_length=32,
                                              blank=True)
    click_secret_key_enc = models.TextField(blank=True, editable=False)

    mxik_code = models.CharField("MXIK (IKPU) kodi", max_length=32, blank=True)
    package_code = models.CharField("Qadoq kodi", max_length=32, blank=True)
    vat_percent = models.PositiveSmallIntegerField("QQS foizi", null=True, blank=True)

    payme_secret_key = _secret("payme_secret_key")
    payme_test_secret_key = _secret("payme_test_secret_key")
    click_secret_key = _secret("click_secret_key")

    class Meta:
        verbose_name = "To'lov sozlamalari"
        verbose_name_plural = "To'lov sozlamalari"

    def __str__(self) -> str:
        return "To'lov sozlamalari"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls) -> "PaymentConfig":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def payme_ready(self) -> bool:
        return bool(self.payme_enabled and self.payme_merchant_id and self.payme_secret_key)

    def click_ready(self) -> bool:
        return bool(self.click_enabled and self.click_service_id and self.click_merchant_id
                    and self.click_secret_key)

    def allowed_ip_list(self) -> list[str]:
        return [x.strip() for x in re.split(r"[,\n]", self.payme_allowed_ips or "") if x.strip()]


class ProOrder(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Kutilmoqda"
        PAID = "paid", "To'langan"
        CANCELLED = "cancelled", "Bekor qilingan"
        REFUNDED = "refunded", "Qaytarilgan"

    # Hisob o'chirilsa ham to'lov yozuvi qoladi (buxgalteriya, Payme tekshiruvlari).
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="pro_orders", verbose_name="Foydalanuvchi",
    )
    plan = models.ForeignKey(ProPlan, on_delete=models.PROTECT, related_name="orders",
                             verbose_name="Tarif")
    # Yaratilgan paytdagi nusxa — tarif keyin o'zgarsa ham buyurtma o'zgarmaydi.
    title = models.CharField("Tarif nomi", max_length=120)
    days = models.PositiveIntegerField("Kunlar")
    amount = models.PositiveIntegerField("Summa (so'm)")
    provider = models.CharField("Provayder", max_length=10, choices=Provider.choices)
    status = models.CharField("Holat", max_length=10, choices=Status.choices,
                              default=Status.PENDING, db_index=True)
    granted_days = models.PositiveIntegerField("Berilgan kunlar", default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["user", "-created_at"])]
        verbose_name = "PRO buyurtma"
        verbose_name_plural = "PRO buyurtmalar"

    def __str__(self) -> str:
        return f"#{self.pk} · {self.provider} · {self.amount} · {self.status}"


class ProviderTransaction(models.Model):
    """Provayder tomondagi tranzaksiya (Payme `id` / Click `click_trans_id`)."""

    CREATED = 1
    PERFORMED = 2
    CANCELLED = -1
    CANCELLED_AFTER_PERFORM = -2

    order = models.ForeignKey(ProOrder, on_delete=models.CASCADE, related_name="transactions")
    provider = models.CharField(max_length=10, choices=Provider.choices)
    external_id = models.CharField(max_length=64)
    state = models.SmallIntegerField(default=CREATED)
    amount = models.PositiveIntegerField("Summa (so'm)")
    create_time = models.DateTimeField()
    perform_time = models.DateTimeField(null=True, blank=True)
    cancel_time = models.DateTimeField(null=True, blank=True)
    reason = models.SmallIntegerField(null=True, blank=True)
    extra = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-create_time",)
        unique_together = ("provider", "external_id")
        verbose_name = "Provayder tranzaksiyasi"
        verbose_name_plural = "Provayder tranzaksiyalari"

    def __str__(self) -> str:
        return f"{self.provider}:{self.external_id} ({self.state})"
