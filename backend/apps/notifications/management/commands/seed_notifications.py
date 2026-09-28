"""Creates a few demo broadcast notifications (development helper)."""

from django.core.management.base import BaseCommand

from apps.notifications.models import Notification

DEMO = [
    {
        "kind": Notification.Kind.EXAM,
        "title_uz": "Imtihon vaqti keldi",
        "title_ru": "Время экзамена",
        "title_cry": "Имтиҳон вақти келди",
        "body_uz": "Bugun 20 ta savoldan iborat sinov imtihonini yechib ko'ring.",
        "body_ru": "Пройдите сегодня пробный экзамен из 20 вопросов.",
        "body_cry": "Бугун 20 та саволдан иборат синов имтиҳонини ечиб кўринг.",
    },
    {
        "kind": Notification.Kind.LESSON,
        "title_uz": "Yangi dars qo'shildi",
        "title_ru": "Добавлен новый урок",
        "title_cry": "Янги дарс қўшилди",
        "body_uz": "\"Yo'l belgilari\" bo'limiga yangi dars qo'shildi.",
        "body_ru": "В раздел «Дорожные знаки» добавлен новый урок.",
        "body_cry": "«Йўл белгилари» бўлимига янги дарс қўшилди.",
    },
    {
        "kind": Notification.Kind.PRO,
        "title_uz": "PRO obuna chegirmasi",
        "title_ru": "Скидка на PRO подписку",
        "title_cry": "PRO обуна чегирмаси",
        "body_uz": "Faqat shu hafta PRO obunaga 30% chegirma.",
        "body_ru": "Только на этой неделе скидка 30% на PRO подписку.",
        "body_cry": "Фақат шу ҳафта PRO обунага 30% чегирма.",
    },
]


class Command(BaseCommand):
    help = "Demo bildirishnomalar yaratadi"

    def handle(self, *args, **options):
        created = 0
        for row in DEMO:
            _, made = Notification.objects.get_or_create(
                title_uz=row["title_uz"], defaults=row
            )
            created += int(made)
        self.stdout.write(
            self.style.SUCCESS(
                f"{created} ta yangi bildirishnoma (jami: {Notification.objects.count()})"
            )
        )
