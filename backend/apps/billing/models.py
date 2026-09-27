"""Filial va to'lovlar — eski `web/backend` dagi `home` app'idan ko'chdi.

Farqi: to'lov `Student` emas, `User` ga bog'lanadi — yagona bazada o'quvchi ham
foydalanuvchi.
"""

from datetime import date
from decimal import Decimal

from django.conf import settings
from django.db import models, transaction
from django.db.models import F


class Branch(models.Model):
    name = models.CharField(max_length=100, verbose_name="Filial nomi")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "Filial"
        verbose_name_plural = "Filiallar"

    def __str__(self) -> str:
        return self.name


class StudentPayment(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="payment", verbose_name="O'quvchi",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Summa")
    tolagani = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0"), verbose_name="To'lagani"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "To'lov"
        verbose_name_plural = "To'lovlar"

    def __str__(self) -> str:
        return f"{self.user_id} · {self.tolagani}/{self.amount}"

    @property
    def qoldiq(self) -> Decimal:
        return self.amount - self.tolagani


class PaymentReport(models.Model):
    student_payment = models.ForeignKey(
        StudentPayment, on_delete=models.CASCADE, related_name="reports",
        verbose_name="To'lov",
    )
    paid_amount = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name="To'langan summa"
    )
    date = models.DateField(default=date.today, verbose_name="Hisobot sanasi")
    comment = models.TextField(blank=True, verbose_name="Izoh")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-date", "-created_at")
        verbose_name = "To'lov hisoboti"
        verbose_name_plural = "To'lov hisobotlari"

    def __str__(self) -> str:
        return f"{self.date} · {self.paid_amount}"

    def save(self, *args, **kwargs):
        """Yangi hisobot `tolagani` ni oshiradi.

        `F()` bilan — ikki hisobot bir vaqtda kelsa biri ikkinchisini yo'qotmasin.
        """
        creating = self._state.adding
        with transaction.atomic():
            super().save(*args, **kwargs)
            if creating:
                StudentPayment.objects.filter(pk=self.student_payment_id).update(
                    tolagani=F("tolagani") + self.paid_amount
                )
