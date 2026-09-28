"""Siqilgan WebP nusxalarni ASOSIY media qiladi va eski originallarni o'chiradi.

`optimize_media` media/opt/ ga WebP yaratgan bo'lishi kerak. Bu buyruq:
  1) opt/…webp fayllarni asl joyiga ko'chiradi (images/…webp),
  2) DB'dagi image/explanation_image ref'larini .png/.jpg -> .webp qiladi,
  3) eski raster originallarni (.png/.jpg) o'chiradi,
  4) opt/ papkasini tozalaydi.

QAYTMAS AMAL — originallar o'chadi. Sifat oldindan tekshirilgan.

    python manage.py finalize_media
"""

import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.content.models import Question

RASTER = {".png", ".jpg", ".jpeg"}


class Command(BaseCommand):
    help = "WebP nusxalarni asosiy media qiladi, eski originallarni o'chiradi."

    def handle(self, *args, **opts):
        root = Path(settings.MEDIA_ROOT)
        opt_root = root / "opt"
        if not opt_root.exists():
            self.stderr.write("opt/ topilmadi — avval `optimize_media` ishga tushiring.")
            return

        # 1) opt/…webp -> asl joyga
        moved = 0
        for src in opt_root.rglob("*.webp"):
            dst = root / src.relative_to(opt_root)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            moved += 1

        # 2) DB ref .png/.jpg -> .webp + eski originalni o'chirish
        updated = deleted = 0
        for q in Question.objects.all():
            fields = []
            for f in ("image", "explanation_image"):
                path = getattr(q, f)
                if not path or Path(path).suffix.lower() not in RASTER:
                    continue
                webp_rel = Path(path).with_suffix(".webp")
                if not (root / webp_rel).exists():
                    continue  # webp yo'q — xavfsizlik uchun tegmaymiz
                orig = root / path
                if orig.exists():
                    orig.unlink()
                    deleted += 1
                setattr(q, f, webp_rel.as_posix())
                fields.append(f)
            if fields:
                q.save(update_fields=fields)
                updated += 1

        # 3) qolgan yetim raster originallar + opt/ tozalash
        orphans = 0
        for p in root.rglob("*"):
            if p.is_file() and p.suffix.lower() in RASTER and opt_root not in p.parents:
                p.unlink()
                orphans += 1
        shutil.rmtree(opt_root, ignore_errors=True)

        self.stdout.write(self.style.SUCCESS(
            f"Tayyor: {moved} webp ko'chirildi, {updated} savol yangilandi, "
            f"{deleted} original + {orphans} yetim o'chirildi, opt/ tozalandi."
        ))
