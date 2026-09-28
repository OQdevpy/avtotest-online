"""Eski frontlar uchun maydon taxalluslari.

`web/frontend` va desktop `darslik` eski nomlarni kutadi (`question_uz`,
`answer_uz`, `tartib`). Ularni har bir javobga qo'shish mobil trafikni
semirtiradi, shuning uchun faqat `?compat=1` so'ralganda qo'shiladi.
"""

TRUE_VALUES = ("1", "true", "yes", "on")


def compat_requested(request) -> bool:
    if request is None:
        return False
    value = request.query_params.get("compat", "")
    return str(value).strip().lower() in TRUE_VALUES


class CompatFieldsMixin:
    """`compat_aliases` dagi eski nomlarni javobga qo'shadi.

    Kalit — eski nom, qiymat — model maydoni. Serializer o'zi chiqargan
    maydonlar tegilmaydi.
    """

    compat_aliases: dict[str, str] = {}

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not self.compat_aliases:
            return data
        request = self.context.get("request")
        if not compat_requested(request):
            return data
        for alias, source in self.compat_aliases.items():
            data[alias] = getattr(instance, source, None)
        return data
