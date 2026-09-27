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

    # Tahrirlashda balansni faqat farq bo'yicha tuzatish uchun eski summa.
    # `__init__` da olib bo'lmaydi: Django `_state.adding` ni `from_db()` dan
    # KEYIN False qiladi, shuning uchun bazadan o'qilgan qator ham "yangi"
    # ko'rinadi.
    _original_paid_amount = None

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        instance._original_paid_amount = instance.paid_amount
        return instance

    def save(self, *args, skip_balance: bool = False, **kwargs):
        """Balansni hisobot bilan birga yuritadi.

        Yangi hisobot `tolagani` ni oshiradi, tahrirlangani farq bo'yicha
        tuzatadi. `F()` bilan — ikki hisobot bir vaqtda kelsa biri
        ikkinchisini yo'qotmasin.

        `skip_balance=True` — import uchun: eski bazadan `tolagani` tayyor
        holda kelgan, qayta oshirilmasligi kerak.
        """
        creating = self._state.adding
        previous = self._original_paid_amount
        with transaction.atomic():
            super().save(*args, **kwargs)
            if not skip_balance:
                delta = self.paid_amount if creating else self.paid_amount - (
                    previous if previous is not None else Decimal("0")
                )
                if delta:
                    StudentPayment.objects.filter(pk=self.student_payment_id).update(
                        tolagani=F("tolagani") + delta
                    )
        self._original_paid_amount = self.paid_amount

    def delete(self, *args, **kwargs):
        """Hisobot o'chirilsa balans ham kamayadi."""
        payment_id, amount = self.student_payment_id, self.paid_amount
        with transaction.atomic():
            result = super().delete(*args, **kwargs)
            StudentPayment.objects.filter(pk=payment_id).update(
                tolagani=F("tolagani") - amount
            )
        return result
