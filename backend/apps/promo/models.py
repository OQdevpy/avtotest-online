"""Mobil ilova bosh sahifasidagi karusel slaydlari (admin rasm yuklaydi).

Slayd — faqat rasm: matn va logo rasmning o'zida. Shuning uchun har til uchun
alohida rasm; ruscha yoki kirill bo'lmasa o'zbekchasi ko'rsatiladi.
"""

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

IMAGE_HELP = "Tavsiya: 1200×500 px (2.4:1), JPG/PNG/WEBP, 1 MB gacha. Matn va logo rasmning o'zida."
image_validators = [FileExtensionValidator(["jpg", "jpeg", "png", "webp"])]
MAX_IMAGE_BYTES = 2 * 1024 * 1024


def validate_size(f):
    if f and f.size > MAX_IMAGE_BYTES:
        raise ValidationError("Rasm 2 MB dan katta bo'lmasin.")


class Slide(models.Model):
    class Action(models.TextChoices):
        NONE = "none", "Hech narsa"
        PRO = "pro", "PRO sahifasi"
        LESSONS = "lessons", "Darslar"
        BILETLAR = "biletlar", "Biletlar"
        EXAM = "exam", "Imtihon"
        URL = "url", "Havola (sayt / Telegram)"

    class Audience(models.TextChoices):
        ALL = "all", "Hammaga"
        GUEST = "guest", "Faqat mehmonlarga"
        FREE = "free", "PRO'si yo'qlarga"
        PRO = "pro", "Faqat PRO'larga"

    title = models.CharField("Nomi (faqat admin uchun)", max_length=120)
    image_uz = models.ImageField("Rasm (o'zbekcha)", upload_to="slides/", help_text=IMAGE_HELP,
                                 validators=[*image_validators, validate_size])
    image_ru = models.ImageField("Rasm (русский)", upload_to="slides/", blank=True,
                                 help_text="Bo'sh bo'lsa o'zbekchasi ko'rinadi.",
                                 validators=[*image_validators, validate_size])
    image_cry = models.ImageField("Rasm (кирилл)", upload_to="slides/", blank=True,
                                  help_text="Bo'sh bo'lsa o'zbekchasi ko'rinadi.",
                                  validators=[*image_validators, validate_size])
    action = models.CharField("Bosilganda", max_length=16, choices=Action.choices,
                              default=Action.NONE)
    url = models.URLField("Havola", blank=True, help_text="Faqat «Havola» tanlanganda.")
    audience = models.CharField("Kimga", max_length=16, choices=Audience.choices,
                                default=Audience.ALL)
    order = models.PositiveIntegerField("Tartib", default=0)
    is_active = models.BooleanField("Faol", default=True)
    starts_at = models.DateTimeField("Ko'rinish boshlanishi", null=True, blank=True)
    ends_at = models.DateTimeField("Ko'rinish tugashi", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("order", "id")
        verbose_name = "Slayd"
        verbose_name_plural = "Karusel slaydlari"

    def __str__(self) -> str:
        return self.title

    def clean(self):
        if self.action == self.Action.URL and not self.url:
            raise ValidationError({"url": "«Havola» uchun manzil kiriting."})
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError({"ends_at": "Tugash vaqti boshlanishdan keyin bo'lsin."})

    def image_for(self, lang: str):
        """lang — saqlash ustuni (uz / ru / cry)."""
        return getattr(self, f"image_{lang}", None) or self.image_uz

    @classmethod
    def visible_to(cls, user):
        now = timezone.now()
        audiences = [cls.Audience.ALL]
        if getattr(user, "pro_active", False):
            audiences.append(cls.Audience.PRO)
        else:
            audiences.append(cls.Audience.FREE)
        if getattr(user, "is_guest", False):
            audiences.append(cls.Audience.GUEST)
        return cls.objects.filter(
            is_active=True, audience__in=audiences,
        ).filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=now),
            Q(ends_at__isnull=True) | Q(ends_at__gt=now),
        )
