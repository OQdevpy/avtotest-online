"""Django settings for the Yo'lchi / Avtotestga tayyorlov backend."""

from datetime import timedelta
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def env_bool(key: str, default: bool = False) -> bool:
    return env(key, str(default)).lower() in ("1", "true", "yes", "on")


def env_list(key: str, default: str = "") -> list[str]:
    return [x.strip() for x in env(key, default).split(",") if x.strip()]


DEBUG = env_bool("DEBUG", False)

# Prodda SECRET_KEY majburiy. DEBUG=True bo'lsa lokal ishlash uchun
# vaqtinchalik kalit generatsiya qilinadi (sessiyalar qayta ishga tushganda uziladi).
SECRET_KEY = env("SECRET_KEY")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("SECRET_KEY kerak (DEBUG=False bo'lganda majburiy)")
    from django.core.management.utils import get_random_secret_key

    SECRET_KEY = get_random_secret_key()

# ALLOWED_HOSTS ham prodda majburiy — "*" endi default emas.
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver" if DEBUG else "")
if not DEBUG and not ALLOWED_HOSTS:
    raise ImproperlyConfigured("ALLOWED_HOSTS kerak (DEBUG=False bo'lganda majburiy)")

# nginx HTTPS'ni tugatib, konteynerga http bilan uzatadi. Django so'rovni HTTPS
# deb bilishi uchun X-Forwarded-Proto'ga ishonadi (admin/CSRF/secure cookies).
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# Admin login CSRF — Django 4+ sxema bilan ishonchli originni talab qiladi.
CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS",
    "https://mobile.avtotest-tayyorlov.uz",
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third party
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    # local
    "apps.accounts",
    "apps.billing",
    "apps.content",
    "apps.exams",
    "apps.progress",
    "apps.notifications",
    "apps.telegramauth",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- Database ---------------------------------------------------------------
# Baza faqat DATABASE_URL orqali sozlanadi:
#   postgresql://user:parol@localhost:5432/avtotest
#   postgresql://user:parol@host.docker.internal:5432/avtotest   (konteyner ichidan
#       host mashinadagi Postgres'ga ulanish uchun)
#   sqlite:///db.sqlite3   (faqat eski bazadan dumpdata olish kabi hollarda)
# Qo'shimcha ravishda ?sslmode=require kabi parametrlar OPTIONS'ga uzatiladi.


def database_from_url(url: str) -> dict:
    """DATABASE_URL ni Django DATABASES["default"] lug'atiga aylantiradi."""
    parsed = urlparse(url)
    scheme = parsed.scheme.split("+")[0]

    if scheme in ("sqlite", "sqlite3"):
        # sqlite:///rel/path yoki sqlite:////abs/path
        path = unquote(parsed.path)
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": path.lstrip("/") or str(BASE_DIR / "db.sqlite3"),
        }

    if scheme not in ("postgres", "postgresql", "psql"):
        raise ImproperlyConfigured(f"DATABASE_URL: qo'llab-quvvatlanmaydigan sxema '{scheme}'")

    options = {k: v[0] for k, v in parse_qs(parsed.query).items()}
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(parsed.path).lstrip("/"),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": unquote(parsed.hostname or "127.0.0.1"),
        "PORT": str(parsed.port or "5432"),
        "OPTIONS": options,
    }


if not env("DATABASE_URL"):
    raise ImproperlyConfigured(
        "DATABASE_URL kerak, masalan: postgresql://postgres:parol@localhost:5432/avtotest"
    )

DATABASES = {"default": database_from_url(env("DATABASE_URL"))}

AUTH_USER_MODEL = "accounts.User"

# Ko'chirilgan bazadagi parollar MD5 bilan hash qilingan (test sozlamalarida
# import qilingan). MD5 faqat TEKSHIRISH uchun oxirida turadi: foydalanuvchi
# kirganda Django parolni avtomatik birinchi hasher (PBKDF2) ga o'tkazadi.
# Barcha hisoblar yangilangach bu qatorni olib tashlash mumkin.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Parol uchun yagona shart — kamida 6 belgi. Boshqa cheklovlar yo'q
# (raqamli, "oddiy parol", ismga o'xshash — hammasi ruxsat). Foydalanuvchiga
# lokalizatsiyalangan "kamida 6 belgi" xabari ilovada (err_pass_short) ko'rsatiladi.
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 6},
    },
]

LANGUAGE_CODE = "uz"
TIME_ZONE = env("TIME_ZONE", "Asia/Tashkent")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = env("MEDIA_ROOT") or BASE_DIR / "media"

# WhiteNoise — DEBUG=False bo'lganda ham statik fayllarni (admin, redoc)
# alohida nginx'siz uzatadi.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- DRF --------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "common.pagination.DefaultPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=90),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Avtotestga tayyorlov API",
    "DESCRIPTION": (
        "Yo'lchi mobil ilovasi uchun backend. Barcha kontent uch tilda "
        "(uz / ru / cry) saqlanadi va `?lang=` parametri orqali tanlanadi."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

# --- CORS -------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = env_bool("CORS_ALLOW_ALL", False)
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS")

# --- Project-specific -------------------------------------------------------
# Exam rules mirrored from the mobile Exam screen (20/50 question modes).
EXAM_MODES = {
    20: {"questions": 20, "minutes": 25, "pass_score": 18},
    50: {"questions": 50, "minutes": 45, "pass_score": 46},
}
# A lesson counts as "done" at this ratio of correct answers.
LESSON_PASS_RATIO = 0.7
# A lesson is shown "green" (mastered) at this ratio; attempted below it is "red".
LESSON_GREEN_RATIO = 0.9

# --- Sessiya va qurilma -----------------------------------------------------
# Bir foydalanuvchi bir platformada nechta qurilmadan kira oladi.
# User.max_devices to'ldirilgan bo'lsa u barcha platformalar uchun ustun turadi.
MAX_DEVICES_PER_PLATFORM = {"mobile": 2, "web": 1, "desktop": 1}
# Limit to'lganda 403 o'rniga eng eski sessiya yopiladigan platformalar.
# Mobil ilova chiqishda /auth/logout/ ni chaqirmaydi, shuning uchun busiz
# foydalanuvchi qayta kirganda bloklanib qolardi. Web/desktopda kirish
# sotiladi — u yerda limit qat'iy qoladi.
DEVICE_EVICT_OLDEST = {"mobile"}
# Qurilma sessiyasining umri, kunda. None — muddat yo'q (refresh tokenning
# o'z umri amal qiladi). Web va desktopda kirish sotilgani uchun 12 kun.
SESSION_DAYS = {"mobile": None, "web": 12, "desktop": 12}
# Shef chiqargan kirish kodi faollashtirilgandan keyin qancha kun ishlaydi.
ACCESS_CODE_DAYS = 12

# --- Telegram bot -----------------------------------------------------------
# Tasdiqlash kodlari SMS o'rniga Telegram bot orqali yuboriladi.
# Token faqat .env'da saqlanadi (hech qachon kodga yozilmaydi).
TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN")

# --- Ijtimoiy kirish --------------------------------------------------------
# Provayder sozlanmagan bo'lsa u orqali kirish ham ochilmaydi — token
# tekshiruvisiz ishlash imkoni yo'q (apps/accounts/social.py).
APPLE_BUNDLE_ID = env("APPLE_BUNDLE_ID")
GOOGLE_CLIENT_IDS = env_list("GOOGLE_CLIENT_IDS")

# --- Redis ------------------------------------------------------------------
# Bir martalik tasdiqlash kodlari (OTP) TTL bilan Redis'da saqlanadi
# (bazada emas). Bog'lanish (TelegramAccount) esa Postgres'da qoladi.
REDIS_URL = env("REDIS_URL", "redis://localhost:6379/0")
