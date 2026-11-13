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
    /start <token> (ilova havolasi) -> «Kontaktni ulashish» -> natija xabari.
Natija xabarlari ostida «Ilovaga qaytish» inline tugmasi bo'ladi (APP_RETURN_URL).
"""

from __future__ import annotations

import logging

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from telegram import (
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.error import BadRequest
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from apps.accounts.models import User, normalize_phone
from apps.telegramauth import telegram as tg, verification
from apps.telegramauth.models import TelegramAccount

logger = logging.getLogger(__name__)


# --- ORM yordamchilari (async kontekstdan chaqiriladi) --------------------

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


def _return_keyboard(lang: str) -> InlineKeyboardMarkup | None:
    """«Ilovaga qaytish» inline tugmasi (APP_RETURN_URL bo'lmasa None)."""
    data = tg.return_markup(lang)
    if data is None:
        return None
    button = data["inline_keyboard"][0][0]
    return InlineKeyboardMarkup([[InlineKeyboardButton(button["text"], url=button["url"])]])


async def _reply_with_return(message, text: str, lang: str) -> None:
    """Xabarni «Ilovaga qaytish» tugmasi bilan yuboradi.

    Telegram tugma manzilini rad etsa (masalan noto'g'ri APP_RETURN_URL), xabar
    tugmasiz ketadi — tasdiqlash natijasi baribir foydalanuvchiga yetadi.
    """
    keyboard = _return_keyboard(lang)
    if keyboard is not None:
        try:
            await message.reply_text(text, reply_markup=keyboard)
            return
        except BadRequest as exc:
            logger.warning("Ilovaga qaytish tugmasi rad etildi: %s", exc)
    await message.reply_text(text, reply_markup=ReplyKeyboardRemove())


# Eski versiyada pastda doimiy turgan «Kodni olish» tugmasining matnlari. Bunday
# foydalanuvchi uni bossa, tugma olib tashlanadi — kod bot orqali berilmaydi.
LEGACY_CODE_LABELS = {"🔐 Kodni olish", "🔐 Кодни олиш", "🔐 Получить код"}


@sync_to_async
def open_session(telegram_id: int, token: str) -> dict | None:
    """Ilova havolasidagi sessiyani shu chatga bog'laydi (yo'q bo'lsa None)."""
    session = verification.get_session(token)
    if session is not None:
        verification.bind_chat(telegram_id, token)
    return session


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Ilova havolasi (t.me/...?start=<token>) — til so'ralmaydi, darhol bitta
    # «Kontaktni ulashish» tugmasi. Parametrsiz /start — eski oqim (til -> kontakt).
    if context.args:
        session = await open_session(update.effective_user.id, context.args[0])
        if session is None:
            await update.message.reply_text(tg.t("link_expired", "uz"))
            return
        lang = tg.app_lang_to_bot(session["lang"])
        await update.message.reply_text(
            tg.t("verify_prompt", lang), reply_markup=_contact_keyboard(lang),
        )
        return

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

    token = await sync_to_async(verification.chat_token)(from_user.id)
    if token:
        await on_app_contact(message, token, lang)
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

    await _reply_with_return(message, tg.t("linked", lang, phone=phone), lang)


async def on_app_contact(message, token: str, lang: str) -> None:
    """Ilova havolasi bilan kelgan kontakt: raqamni sessiyadagi bilan solishtiradi."""
    from_user = message.from_user
    session = await sync_to_async(verification.get_session)(token)
    if session is not None:
        lang = tg.app_lang_to_bot(session["lang"])
    outcome, entered, shared = await sync_to_async(verification.resolve_contact)(
        token, message.contact.phone_number, from_user.id,
    )
    await sync_to_async(verification.unbind_chat)(from_user.id)
    if outcome == "verified":
        await link_contact(from_user.id, shared, from_user.username or "",
                           from_user.full_name or "")
        text = tg.t("verified", lang)
    elif outcome == "mismatch":
        text = tg.t("mismatch", lang, shared=verification.mask_phone(shared),
                    entered=verification.mask_phone(entered))
    elif outcome == "foreign":
        text = tg.t("foreign_number", lang)
    else:
        text = tg.t("link_expired", lang)
    # Har qanday natijadan keyin ham ilovaga bir bosishda qaytish mumkin.
    await _reply_with_return(message, text, lang)


async def on_legacy_code_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Eski «Kodni olish» tugmasi bosildi: uni klaviaturadan olib tashlaymiz."""
    lang = await get_language(update.message.from_user.id)
    await update.message.reply_text(
        tg.t("keyboard_removed", lang), reply_markup=ReplyKeyboardRemove(),
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
        # Eski versiyadan qolgan «Kodni olish» tugmasini tozalash.
        app.add_handler(
            MessageHandler(filters.Text(LEGACY_CODE_LABELS), on_legacy_code_button)
        )

        self.stdout.write(self.style.SUCCESS(
            f"Bot ishga tushdi (@{tg.BOT_USERNAME}). To'xtatish: Ctrl+C"
        ))
        app.run_polling(allowed_updates=Update.ALL_TYPES)
