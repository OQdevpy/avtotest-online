"""Telegram Bot API bilan ishlash: til xaritalash, matnlar va sendMessage.

Kod yetkazish (``sendMessage``) veb-endpointdan to'g'ridan-to'g'ri sinxron
HTTPS chaqiruv orqali amalga oshiriladi — bu bilan veb-so'rov bot jarayoniga
(``runbot``) bog'liq bo'lmaydi. Ikkalasi ham bitta tokendan foydalanadi.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)

BOT_USERNAME = "AvtotestTayyorlovBot"
BOT_LINK = f"https://t.me/{BOT_USERNAME}"


def bot_token() -> str:
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "") or ""
    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN sozlanmagan. .env fayliga qo'shing."
        )
    return token


def app_lang_to_bot(lang: str | None) -> str:
    """Ilova tili (uz/kr/qq/ru) -> bot tili (uz/kr/ru).

    `qq` (qoraqalpoq) uchun ham `uz` (lotin) ishlatiladi.
    """
    mapping = {"uz": "uz", "kr": "kr", "qq": "uz", "ru": "ru"}
    return mapping.get((lang or "").lower(), "uz")


# --- Foydalanuvchiga ko'rinadigan matnlar ---------------------------------
# Barcha bot matnlari uchta tilda. `{code}` va `{minutes}` o'rniga qiymat
# qo'yiladi.

TEXTS: dict[str, dict[str, str]] = {
    "choose_language": {
        "uz": "Tilni tanlang / Тилни танланг / Выберите язык:",
        "kr": "Тилни танланг:",
        "ru": "Выберите язык:",
    },
    "welcome": {
        "uz": (
            "Assalomu alaykum! Bu — Avtotestga tayyorlov ilovasining tasdiqlash "
            "boti.\n\nRaqamingizni ilovaga bog'lash uchun pastdagi "
            "«📱 Kontaktni ulashish» tugmasini bosing."
        ),
        "kr": (
            "Ассалому алайкум! Бу — Автотестга тайёрлов иловасининг тасдиқлаш "
            "боти.\n\nРақамингизни иловага боғлаш учун пастдаги "
            "«📱 Контактни улашиш» тугмасини босинг."
        ),
        "ru": (
            "Здравствуйте! Это бот подтверждения приложения «Автотест».\n\n"
            "Чтобы привязать ваш номер, нажмите кнопку «📱 Поделиться контактом» ниже."
        ),
    },
    "share_contact": {
        "uz": "📱 Kontaktni ulashish",
        "kr": "📱 Контактни улашиш",
        "ru": "📱 Поделиться контактом",
    },
    "linked": {
        "uz": (
            "✅ Raqamingiz bog'landi: {phone}\n\nEndi ilovada «Kodni olish» "
            "tugmasini bossangiz, tasdiqlash kodi shu yerga keladi."
        ),
        "kr": (
            "✅ Рақамингиз боғланди: {phone}\n\nЭнди иловада «Кодни олиш» "
            "тугмасини боссангиз, тасдиқлаш коди шу ерга келади."
        ),
        "ru": (
            "✅ Ваш номер привязан: {phone}\n\nТеперь при нажатии «Получить код» "
            "в приложении код придёт сюда."
        ),
    },
    "not_own_contact": {
        "uz": "⚠️ Iltimos, faqat o'zingizning kontaktingizni ulashing.",
        "kr": "⚠️ Илтимос, фақат ўзингизнинг контактингизни улашинг.",
        "ru": "⚠️ Пожалуйста, делитесь только своим контактом.",
    },
    "get_code_button": {
        "uz": "🔐 Kodni olish",
        "kr": "🔐 Кодни олиш",
        "ru": "🔐 Получить код",
    },
    "not_linked_yet": {
        "uz": (
            "Avval raqamingizni bog'lang. /start bosing va «📱 Kontaktni "
            "ulashish» tugmasi orqali raqamingizni yuboring."
        ),
        "kr": (
            "Аввал рақамингизни боғланг. /start босинг ва «📱 Контактни "
            "улашиш» тугмаси орқали рақамингизни юборинг."
        ),
        "ru": (
            "Сначала привяжите номер. Нажмите /start и отправьте контакт "
            "кнопкой «📱 Поделиться контактом»."
        ),
    },
    # {code} <code>...</code> ichida — Telegram'da monospace bo'lib, ustiga
    # bosganda avtomatik nusxa olinadi (parse_mode="HTML" bilan yuboriladi).
    "code_message": {
        "uz": (
            "🔐 Tasdiqlash kodingiz: <code>{code}</code>\n\nKod {minutes} daqiqa amal qiladi. "
            "Uni hech kimga bermang."
        ),
        "kr": (
            "🔐 Тасдиқлаш кодингиз: <code>{code}</code>\n\nКод {minutes} дақиқа амал қилади. "
            "Уни ҳеч кимга берманг."
        ),
        "ru": (
            "🔐 Ваш код подтверждения: <code>{code}</code>\n\nКод действует {minutes} минут. "
            "Никому его не сообщайте."
        ),
    },
}


def t(key: str, lang: str, **kwargs) -> str:
    lang = lang if lang in ("uz", "kr", "ru") else "uz"
    template = TEXTS[key].get(lang) or TEXTS[key]["uz"]
    return template.format(**kwargs) if kwargs else template


def send_message(
    chat_id: int, text: str, *, parse_mode: str | None = None, timeout: float = 10.0
) -> bool:
    """``sendMessage`` ni sinxron HTTPS orqali yuboradi.

    Muvaffaqiyatda True, aks holda False (log yoziladi). Bu funksiya
    veb-so'rov ichida chaqiriladi, shuning uchun tashqi tarmoq xatosida
    ham serverni "yiqitmasligi" kerak. `parse_mode="HTML"` — kod <code>…</code>
    ichida monospace/nusxa-olinadigan bo'lishi uchun.
    """
    url = f"https://api.telegram.org/bot{bot_token()}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    if parse_mode:
        data["parse_mode"] = parse_mode
    payload = json.dumps(data).encode()
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode())
        if not body.get("ok"):
            logger.warning("sendMessage muvaffaqiyatsiz: %s", body)
            return False
        return True
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        logger.warning("sendMessage HTTP xatosi %s: %s", exc.code, detail)
        return False
    except Exception as exc:  # noqa: BLE001 — tarmoq/timeout hammasi ushlanadi
        logger.warning("sendMessage xatosi: %s", exc)
        return False
