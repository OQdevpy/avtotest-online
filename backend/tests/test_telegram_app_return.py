"""Botdan ilovaga qaytish: https ko'prik sahifa va inline tugma."""

import pytest

from apps.telegramauth import telegram as tg

URL = "/api/v1/auth/telegram/return/"


def test_return_page_opens_app(client, settings):
    settings.APP_SCHEME = "prava777"
    settings.APP_ANDROID_PACKAGE = "com.example.app"
    r = client.get(URL)
    assert r.status_code == 200
    body = r.content.decode()
    assert "intent://open#Intent;scheme=prava777;package=com.example.app;end" in body
    assert "prava777://open" in body


def test_return_page_needs_no_auth(api):
    # Telegram brauzeri token yubormaydi.
    assert api.get(URL).status_code == 200


def test_return_button_uses_setting(settings):
    settings.APP_RETURN_URL = "https://example.uz/api/v1/auth/telegram/return/"
    markup = tg.return_markup("uz")
    button = markup["inline_keyboard"][0][0]
    assert button["url"] == settings.APP_RETURN_URL
    assert "PRAVA777" in button["text"]


def test_no_return_button_without_setting(settings):
    settings.APP_RETURN_URL = ""
    assert tg.return_markup("ru") is None


@pytest.mark.parametrize("lang", ["uz", "kr", "ru"])
def test_bot_texts_do_not_offer_code(lang):
    for key in tg.TEXTS:
        text = tg.TEXTS[key].get(lang, "")
        assert "Kodni olish" not in text
        assert "Кодни олиш" not in text
        assert "Получить код" not in text
    assert "get_code_button" not in tg.TEXTS
