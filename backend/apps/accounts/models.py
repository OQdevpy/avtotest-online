import hashlib
import re
import secrets
from datetime import timedelta

from django.conf import settings

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


def placeholder_phone(provider: str, uid: str) -> str:
    """Telefonsiz ijtimoiy hisob uchun yaroqli o'rinbosar raqam.

    Apple va Google `uid` lari harf ham saqlaydi, shuning uchun raqamni
    to'g'ridan-to'g'ri undan yasab bo'lmaydi — deterministik hash ishlatiladi.
    Raqam band bo'lsa keyingisi olinadi. Foydalanuvchi haqiqiy raqamini
    kiritgach bu qiymat almashadi.
    """
    digest = hashlib.sha256(f"{provider}:{uid}".encode()).digest()
    base = int.from_bytes(digest[:8], "big") % 1_000_000_000
    for offset in range(1000):
        phone = f"+998{(base + offset) % 1_000_000_000:09d}"
        if not User.objects.filter(phone=phone).exists():
            return phone
    raise ValidationError("O'rinbosar telefon raqam topilmadi.")


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
    branch = models.ForeignKey(
        "billing.Branch", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="users", verbose_name="Filial",
    )
    # Eski web backendidagi maydon — o'quvchi hujjatini topshirganmi.
    hujjat = models.CharField(
        max_length=1, choices=(("+", "+"), ("-", "-")), default="-", verbose_name="Hujjat"
    )
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
        ordering = ("-date_joined", "id")
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


class AccessCode(models.Model):
    """Shef chiqaradigan kirish kodi — desktop darslik va imtihon uchun.

    Eski web backendidagi `Token` modelining o'rinbosari. Kod har doim aniq bir
    foydalanuvchiga tegishli: shef avval o'quvchini yaratadi, keyin unga kod
    beradi — anonim hisob paydo bo'lmaydi. Muddat birinchi ishlatilganda
    boshlanadi, shuning uchun berilgan-u ishlatilmagan kod "yonib ketmaydi".
    """

    # Chalkash belgilar (O/0, I/1) chiqarib tashlangan — kod qo'lda kiritiladi.
    ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    LENGTH = 8

    code = models.CharField(max_length=16, unique=True, db_index=True, verbose_name="Kod")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="access_codes", verbose_name="O'quvchi"
    )
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="issued_access_codes", verbose_name="Kim berdi",
    )
    valid_days = models.PositiveSmallIntegerField(verbose_name="Necha kun")
    created_at = models.DateTimeField(auto_now_add=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, verbose_name="Faol")

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Kirish kodi"
        verbose_name_plural = "Kirish kodlari"

    def __str__(self) -> str:
        return f"{self.code} → {self.user_id}"

    @classmethod
    def new_code(cls) -> str:
        while True:
            code = "".join(secrets.choice(cls.ALPHABET) for _ in range(cls.LENGTH))
            if not cls.objects.filter(code=code).exists():
                return code

    @classmethod
    def generate(cls, *, user, created_by=None, valid_days: int | None = None):
        return cls.objects.create(
            code=cls.new_code(),
            user=user,
            created_by=created_by,
            valid_days=valid_days or settings.ACCESS_CODE_DAYS,
        )

    @property
    def is_usable(self) -> bool:
        if not self.is_active or not self.user.is_active:
            return False
        if self.activated_at is None:
            return True
        return self.expires_at is None or self.expires_at > timezone.now()

    def activate(self) -> None:
        """Muddatni birinchi ishlatishda boshlaydi; keyingilari tegmaydi."""
        if self.activated_at is not None:
            return
        now = timezone.now()
        self.activated_at = now
        self.expires_at = now + timedelta(days=self.valid_days)
        self.save(update_fields=["activated_at", "expires_at"])
