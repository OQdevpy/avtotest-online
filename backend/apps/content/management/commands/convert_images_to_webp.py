"""Savol rasmlarini WebP'ga o'giradi (spec §10, 4-qadam).

Eski web va mobil bazalaridan kelgan PNG/JPG rasmlar birlashtirilganda
ishlatiladi. Idempotent: allaqachon `.webp` bo'lgan yoki fayli topilmagan
yozuvlar o'tkazib yuboriladi.
"""

from pathlib import Path

from django.core.management.base import BaseCommand

from apps.content.media import UnreadableImage, media_path, to_webp, unique_name
from apps.content.models import Question

FIELDS = ("image", "explanation_image")


class Command(BaseCommand):
    help = "Savol rasmlarini WebP formatiga o'giradi"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Nima o'zgarishini ko'rsatadi, hech narsa yozmaydi",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        converted = skipped = missing = failed = 0

        for question in Question.objects.exclude(image="", explanation_image=""):
            changed = {}
            for field in FIELDS:
                relative = getattr(question, field)
                if not relative:
                    continue
                if relative.lower().endswith(".webp"):
                    skipped += 1
                    continue
                source = media_path(relative)
                if not source.exists():
                    missing += 1
                    self.stderr.write(f"topilmadi: {relative}")
                    continue
                if dry_run:
                    converted += 1
                    self.stdout.write(f"o'girilardi: {relative}")
                    continue
                try:
                    new_path = to_webp(source, unique_name(Path(relative).stem))
                except UnreadableImage:
                    failed += 1
                    self.stderr.write(f"o'qilmadi: {relative}")
                    continue
                changed[field] = new_path
                converted += 1

            if changed and not dry_run:
                for field, value in changed.items():
                    setattr(question, field, value)
                question.save(update_fields=list(changed))

        self.stdout.write(
            f"o'girildi: {converted}, o'tkazildi: {skipped}, "
            f"topilmadi: {missing}, xato: {failed}"
        )
