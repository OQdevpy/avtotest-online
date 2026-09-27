import re

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

PHONE_RE = re.compile(r"^\+998\d{9}$")


def normalize_phone(raw: str) -> str:
    """Accept '901234567', '+998 90 123 45 67', '998901234567' -> '+998901234567'."""
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 9:
        digits = "998" + digits
    phone = "+" + digits
    if not PHONE_RE.match(phone):
        raise ValidationError("Telefon raqam +998XXXXXXXXX ko'rinishida bo'lishi kerak.")
    return phone


class UserManager(BaseUserManager):
    def create_user(self, phone: str, password: str | None = None, **extra):
        phone = normalize_phone(phone)
        user = self.model(phone=phone, **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone: str, password: str, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("is_active", True)
        extra.setdefault("role", User.Role.ADMIN)
        if not extra["is_staff"] or not extra["is_superuser"]:
            raise ValueError("Superuser is_staff va is_superuser bo'lishi shart.")
        return self.create_user(phone, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        STUDENT = "student", "O'quvchi"
        TEACHER = "teacher", "O'qituvchi"
        ADMIN = "admin", "Shef"

    class Language(models.TextChoices):
        UZ = "uz", "O'zbekcha (lotin)"
        KR = "kr", "Ўзбекча (кирилл)"
        QQ = "qq", "Qaraqalpaqsha"
        RU = "ru", "Русский"

    phone = models.CharField(max_length=13, unique=True, db_index=True)
    full_name = models.CharField(max_length=120, blank=True)
    role = models.CharField(
        max_length=10, choices=Role.choices, default=Role.STUDENT, db_index=True,
        verbose_name="Rol",
    )
    language = models.CharField(max_length=3, choices=Language.choices, default=Language.UZ)
    dark_theme = models.BooleanField(default=False)

    # PRO subscription (the mobile Home screen shows a PRO banner)
    is_pro = models.BooleanField(default=False)
    pro_until = models.DateTimeField(null=True, blank=True)

    # Null bo'lsa settings.MAX_DEVICES_PER_PLATFORM amal qiladi; to'ldirilgan
    # bo'lsa barcha platformalar uchun shu son ustun turadi.
    max_devices = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name="Qurilma limiti"
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"

    def __str__(self) -> str:
        return f"{self.full_name or 'user'} ({self.phone})"

    @property
    def is_teacher(self) -> bool:
        """O'qituvchi huquqi — o'quvchilar natijasini ko'rish. Shefda ham bor."""
        return self.role in (self.Role.TEACHER, self.Role.ADMIN)

    @property
    def is_content_admin(self) -> bool:
        """Kontent, foydalanuvchi va to'lovni boshqarish huquqi."""
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def pro_active(self) -> bool:
        if not self.is_pro:
            return False
        return self.pro_until is None or self.pro_until > timezone.now()

    @property
    def initials(self) -> str:
        parts = [p for p in self.full_name.split() if p]
        return "".join(p[0].upper() for p in parts[:2]) or self.phone[-2:]


class SocialAccount(models.Model):
    """Links an external identity (Apple / Google / Telegram) to a User.

    The mobile Login screen offers these providers; verification of the
    provider token happens in the auth view before a row is created here.
    """

    class Provider(models.TextChoices):
        APPLE = "apple", "Apple"
        GOOGLE = "google", "Google"
        TELEGRAM = "telegram", "Telegram"
        EMAIL = "email", "Email"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="social_accounts")
    provider = models.CharField(max_length=16, choices=Provider.choices)
    uid = models.CharField(max_length=191)
    email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("provider", "uid")

    def __str__(self) -> str:
        return f"{self.provider}:{self.uid}"


class Device(models.Model):
    """Bitta kirish sessiyasi — kim, qayerdan, qachongacha.

    Eski web backendidagi `Student.is_online` (bitta qurilma) va 12 kunlik
    muddat qoidasi shu jadvalda yashaydi. Refresh tokenning `jti` si shu
    yozuvga bog'lanadi, shuning uchun sessiyani serverdan uzish mumkin.
    """

    class Platform(models.TextChoices):
        MOBILE = "mobile", "Mobil"
        WEB = "web", "Web"
        DESKTOP = "desktop", "Desktop"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="devices")
    platform = models.CharField(
        max_length=10, choices=Platform.choices, default=Platform.MOBILE, db_index=True
    )
    refresh_jti = models.CharField(max_length=64, unique=True)
    label = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ("-last_seen",)
        indexes = [models.Index(fields=["user", "platform", "is_active"])]
        verbose_name = "Qurilma"
        verbose_name_plural = "Qurilmalar"

    def __str__(self) -> str:
        return f"{self.user_id} · {self.platform} · {self.label or 'nomsiz'}"

    @property
    def is_expired(self) -> bool:
        return self.expires_at is not None and self.expires_at <= timezone.now()
