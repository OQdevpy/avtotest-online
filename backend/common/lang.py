"""Language resolution + translated-field helpers.

Content is stored in three columns (`*_uz`, `*_ru`, `*_cry`) exactly like the
legacy `avtotest-desktop-seoul` fixtures. The API flattens them to a single
field chosen by the request, so the mobile client never sees the suffixes.

The mobile app has four language codes; two of them map onto stored columns:
    uz  -> uz      (O'zbekcha, lotin)
    kr  -> cry     (Ўзбекча, кирилл)
    qq  -> uz      (Qaraqalpaqsha — no separate content yet, falls back to uz)
    ru  -> ru
"""

from rest_framework import serializers

# stored columns
DB_LANGS = ("uz", "ru", "cry")
DEFAULT_LANG = "uz"

# client code -> stored column
CLIENT_TO_DB = {
    "uz": "uz",
    "kr": "cry",
    "cry": "cry",
    "qq": "uz",
    "ru": "ru",
}


def resolve_lang(request) -> str:
    """Pick the stored language column for this request.

    Order: `?lang=` query param, then the `Accept-Language` header, then uz.
    """
    raw = ""
    if request is not None:
        raw = (request.query_params.get("lang") or "").strip().lower()
        if not raw:
            header = request.headers.get("Accept-Language", "")
            raw = header.split(",")[0].split("-")[0].strip().lower()
    return CLIENT_TO_DB.get(raw, DEFAULT_LANG)


def pick(obj, base: str, lang: str) -> str:
    """Return `obj.<base>_<lang>`, falling back to uz and then to any value."""
    value = getattr(obj, f"{base}_{lang}", "") or ""
    if value:
        return value
    for fallback in (DEFAULT_LANG, "ru", "cry"):
        value = getattr(obj, f"{base}_{fallback}", "") or ""
        if value:
            return value
    return ""


class TranslatedField(serializers.Field):
    """Read-only field that resolves `<base>_<lang>` for the current request.

    Usage::

        class LessonSerializer(LangSerializerMixin, serializers.ModelSerializer):
            name = TranslatedField("name")
    """

    def __init__(self, base: str, **kwargs):
        self.base = base
        kwargs.setdefault("read_only", True)
        kwargs.setdefault("source", "*")
        super().__init__(**kwargs)

    def to_representation(self, obj) -> str:
        return pick(obj, self.base, self.context.get("lang", DEFAULT_LANG))


class LangSerializerContextMixin:
    """Injects the resolved language into serializer context.

    Mixed into views (not serializers) so nested serializers inherit it.
    """

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["lang"] = resolve_lang(self.request)
        return ctx
