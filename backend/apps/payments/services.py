"""PRO berish va qaytarish — webhook'lar faqat shu funksiyalar orqali o'zgartiradi.

Chaqiruvchi `transaction.atomic()` ichida va buyurtma qatorini
`select_for_update()` bilan qulflagan bo'lishi kerak — bir xabar ikki marta yoki
bir vaqtda kelsa PRO ikki marta qo'shilmaydi.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import PaymentConfig, ProOrder, Provider


def _locked_user(order: ProOrder):
    if order.user_id is None:
        return None
    return get_user_model().objects.select_for_update().filter(pk=order.user_id).first()


def grant_pro(order: ProOrder) -> bool:
    """Buyurtmani to'langan qiladi va PRO'ni uzaytiradi. Takror chaqiruv — `False`."""
    if order.status == ProOrder.Status.PAID:
        return False
    now = timezone.now()
    order.status = ProOrder.Status.PAID
    order.paid_at = now
    order.granted_days = 0

    user = _locked_user(order)
    # Muddatsiz PRO (`is_pro` va `pro_until=None`) — qo'shadigan narsa yo'q.
    if user is not None and not (user.is_pro and user.pro_until is None):
        start = max(now, user.pro_until) if user.pro_until else now
        user.pro_until = start + timedelta(days=order.days)
        user.is_pro = True
        user.save(update_fields=["is_pro", "pro_until"])
        order.granted_days = order.days

    order.save(update_fields=["status", "paid_at", "granted_days"])
    return True


def revoke_pro(order: ProOrder) -> None:
    """To'lov qaytarildi: berilgan kunlar ayiriladi, buyurtma `refunded`."""
    if order.status != ProOrder.Status.PAID:
        return
    now = timezone.now()
    user = _locked_user(order)
    if user is not None and user.pro_until is not None and order.granted_days:
        user.pro_until -= timedelta(days=order.granted_days)
        if user.pro_until <= now:
            user.is_pro = False
        user.save(update_fields=["is_pro", "pro_until"])
    order.status = ProOrder.Status.REFUNDED
    order.cancelled_at = now
    order.save(update_fields=["status", "cancelled_at"])


def cancel_pending(order: ProOrder) -> None:
    """To'lanmagan buyurtma bekor qilindi."""
    if order.status != ProOrder.Status.PENDING:
        return
    order.status = ProOrder.Status.CANCELLED
    order.cancelled_at = timezone.now()
    order.save(update_fields=["status", "cancelled_at"])


def available_providers(config: PaymentConfig, platform: str) -> list[str]:
    """Shu platformada sotib olish mumkin bo'lgan provayderlar (tartib bilan)."""
    selling = config.sell_ios if platform == "ios" else config.sell_android
    if not selling:
        return []
    ready = {Provider.PAYME: config.payme_ready(), Provider.CLICK: config.click_ready()}
    return [str(p) for p in (Provider.PAYME, Provider.CLICK) if ready[p]]
