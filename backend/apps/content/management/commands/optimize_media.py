"""Savol/izoh rasmlarini WebP + resize qilib `media/opt/` ga saqlaydi.

Originallar tegilmaydi. API rasm URL'ini optimallashtirilgan nusxaga
yo'naltiradi (serializer'da), shuning uchun mijozga 3-10x kichik fayl boradi.
Bir marta (yoki yangi rasm qo'shilganda) ishga tushiriladi:

    python manage.py optimize_media           # faqat yangilarini
    python manage.py optimize_media --force    # hammasini qayta
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from PIL import Image

MAX_WIDTH = 900          # telefonda ~350px ko'rsatiladi; 900 retina uchun yetarli
QUALITY = 80
EXTS = {".png", ".jpg", ".jpeg"}


class Command(BaseCommand):
    help = "Rasmlarni WebP + resize qilib media/opt/ ga saqlaydi (tez yuklash)."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Mavjudlarini ham qayta yaratadi")

    def handle(self, *args, **opts):
        root = Path(settings.MEDIA_ROOT)
        opt_root = root / "opt"
        force = opts["force"]
        done = skipped = failed = 0

        for src in root.rglob("*"):
            if not src.is_file() or src.suffix.lower() not in EXTS:
                continue
            rel = src.relative_to(root)
            if rel.parts and rel.parts[0] == "opt":
                continue  # o'zimiz yaratgan nusxalar
            dst = opt_root / rel.with_suffix(".webp")
            if dst.exists() and not force:
                skipped += 1
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                with Image.open(src) as im:
                    has_alpha = im.mode in ("RGBA", "LA", "P")
                    im = im.convert("RGBA" if has_alpha else "RGB")
                    if im.width > MAX_WIDTH:
                        h = round(im.height * MAX_WIDTH / im.width)
                        im = im.resize((MAX_WIDTH, h), Image.LANCZOS)
                    im.save(dst, "WEBP", quality=QUALITY, method=4)
                done += 1
                if done % 100 == 0:
                    self.stdout.write(f"  ... {done} ta")
            except Exception as exc:  # noqa: BLE001
                failed += 1
                self.stderr.write(f"skip {rel}: {exc}")

        self.stdout.write(self.style.SUCCESS(
            f"WebP tayyor: {done} yaratildi, {skipped} mavjud, {failed} xato."
        ))
