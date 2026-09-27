"""Telegram bot (polling) — alohida jarayon sifatida ishlaydigan xizmat.

Ishga tushirish::

    .venv/bin/python manage.py runbot

Bot Django ORM'ni ulashadi (til va telefon bog'lanishi bazaga yoziladi).
Kod yetkazish esa veb-endpointdan sinxron HTTPS orqali boradi — ya'ni bu
jarayon o'chib qolsa ham, allaqachon bog'langan foydalanuvchilarga kod
yuborish ishlashda davom etadi.

Oqim:
    /start -> til tanlash (inline tugmalar) -> «Kontaktni ulashish» tugmasi
    -> kontakt ulashilganda telegram_id <-> phone bog'lanadi.
"""

from __future__ import annotations

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from telegram import (
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from apps.accounts.models import User, normalize_phone
from apps.telegramauth import otpstore, telegram as tg
from apps.telegramauth.models import TelegramAccount


# --- ORM yordamchilari (async kontekstdan chaqiriladi) --------------------

@sync_to_async
def get_account(telegram_id: int) -> TelegramAccount | None:
    return TelegramAccount.objects.filter(telegram_id=telegram_id).first()


@sync_to_async
def issue_code_for(telegram_id: int, phone: str) -> str:
    """Bog'langan hisob uchun yangi kod yaratadi (Redis)."""
    return otpstore.issue_code("reset", phone, telegram_id)


@sync_to_async
def get_language(telegram_id: int) -> str:
    acc = TelegramAccount.objects.filter(telegram_id=telegram_id).first()
    return acc.language if acc else "uz"


@sync_to_async
def set_language(telegram_id: int, lang: str, username: str, full_name: str) -> None:
    """Tilni saqlaydi. Hisob bo'lmasa (hali kontakt yo'q) — vaqtincha yaratmaymiz;
    faqat mavjud bo'lsa yangilaymiz, bo'lmasa keyin kontakt kelganda yoziladi."""
    TelegramAccount.objects.update_or_create(
        telegram_id=telegram_id,
        defaults={
            "language": lang,
            "username": username or "",
            "full_name": full_name or "",
        },
    )


@sync_to_async
def link_contact(
    telegram_id: int, phone_raw: str, username: str, full_name: str
) -> tuple[str, str]:
    """Kontaktni bog'laydi. (normalized_phone, language) qaytaradi."""
    phone = normalize_phone(phone_raw)
    acc, _ = TelegramAccount.objects.get_or_create(telegram_id=telegram_id)
    acc.phone = phone
    acc.username = username or acc.username
    acc.full_name = full_name or acc.full_name
    acc.verified_at = timezone.now()
    # Agar shu raqamli foydalanuvchi bo'lsa — bog'laymiz (ixtiyoriy FK).
    acc.user = User.objects.filter(phone=phone).first()
    acc.save()
    return phone, acc.language


# --- Handlerlar -----------------------------------------------------------

def _lang_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="lang:uz")],
            [InlineKeyboardButton("🇺🇿 Ўзбекча", callback_data="lang:kr")],
            [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang:ru")],
        ]
    )


def _contact_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(tg.t("share_contact", lang), request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def _get_code_keyboard(lang: str) -> ReplyKeyboardMarkup:
    """Bog'langandan keyin doimiy «Kodni olish» tugmasi (pastda qoladi)."""
    return ReplyKeyboardMarkup(
        [[KeyboardButton(tg.t("get_code_button", lang))]],
        resize_keyboard=True,
        is_persistent=True,
    )


# Uch tildagi «Kodni olish» tugma matnlari — kelgan xabarni shu bilan solishtiramiz.
GET_CODE_LABELS = {tg.t("get_code_button", lang) for lang in ("uz", "kr", "ru")}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Deep link (t.me/...?start=payload) bo'lsa ham xush kelibsiz -> til ->
    # kontakt oqimi bir xil; payload'ni e'tiborsiz qoldiramiz (kerak bo'lsa
    # context.args orqali olinadi).
    await update.message.reply_text(
        tg.t("choose_language", "uz"),
        reply_markup=_lang_keyboard(),
    )


async def on_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    lang = query.data.split(":", 1)[1]
    if lang not in ("uz", "kr", "ru"):
        lang = "uz"
    user = query.from_user
    await set_language(user.id, lang, user.username or "", user.full_name or "")
    # Xush kelibsiz matni + «Kontaktni ulashish» tugmasi.
    await query.edit_message_text(tg.t("welcome", lang))
    await context.bot.send_message(
        chat_id=user.id,
        text=tg.t("share_contact", lang),
        reply_markup=_contact_keyboard(lang),
    )


async def on_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    contact = message.contact
    from_user = message.from_user
    lang = await get_language(from_user.id)

    # XAVFSIZLIK: faqat o'z kontaktini qabul qilamiz.
    if contact.user_id is None or contact.user_id != from_user.id:
        await message.reply_text(
            tg.t("not_own_contact", lang),
            reply_markup=_contact_keyboard(lang),
        )
        return

    try:
        phone, lang = await link_contact(
            from_user.id,
            contact.phone_number,
            from_user.username or "",
            from_user.full_name or "",
        )
    except Exception:  # noqa: BLE001 — noto'g'ri format bo'lsa
        await message.reply_text(tg.t("not_own_contact", lang))
        return

    await message.reply_text(
        tg.t("linked", lang, phone=phone),
        reply_markup=_get_code_keyboard(lang),
    )


async def on_get_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """«Kodni olish» tugmasi: bog'langan hisob uchun yangi kod generatsiya
    qilib, aynan shu chatga darhol yuboradi (kod Redis'da saqlanadi)."""
    message = update.message
    from_user = message.from_user
    account = await get_account(from_user.id)
    if account is None or not account.phone:
        lang = await get_language(from_user.id)
        await message.reply_text(
            tg.t("not_linked_yet", lang),
            reply_markup=_contact_keyboard(lang),
        )
        return

    lang = account.language
    plain = await issue_code_for(account.telegram_id, account.phone)
    await message.reply_text(
        tg.t("code_message", lang, code=plain, minutes=otpstore.CODE_TTL_SECONDS // 60),
        reply_markup=_get_code_keyboard(lang),
        parse_mode="HTML",
    )


class Command(BaseCommand):
    help = "Telegram tasdiqlash botini (polling) ishga tushiradi"

    def handle(self, *args, **options):
        token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
        if not token:
            raise CommandError(
                "TELEGRAM_BOT_TOKEN sozlanmagan. .env fayliga qo'shing."
            )

        app = ApplicationBuilder().token(token).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(on_language, pattern=r"^lang:"))
        app.add_handler(MessageHandler(filters.CONTACT, on_contact))
        # «Kodni olish» tugmasi (uch tildagi matnlarga mos keladi).
        app.add_handler(
            MessageHandler(filters.Text(GET_CODE_LABELS), on_get_code)
        )

        self.stdout.write(self.style.SUCCESS(
            f"Bot ishga tushdi (@{tg.BOT_USERNAME}). To'xtatish: Ctrl+C"
        ))
        app.run_polling(allowed_updates=Update.ALL_TYPES)
