"""Eski web tizimining to'liq eksportidan (`manage.py dumpdata` JSON) filial
va talabalarni ko'chiradi.

    python manage.py import_student_dump /yo'l/barcha_malumotlar.json [--dry-run]

Faqat `home.branch` va `home.student` o'qiladi — to'lovlar bu buyruqqa
kirmaydi (kerak bo'lsa alohida `import_web` bilan qo'shiladi). Har bir
`Student.save()` `apps.billing.signals` orqali bog'liq `User`ni avtomatik
yaratadi ("student=foydalanuvchi" qoidasi).

**Mavjud yozuv qoidasi.** Telefon bo'yicha `Student` allaqachon bo'lsa, u
qayta yozilmaydi — front-ofis xodimi shu orada tahrirlagan bo'lishi mumkin.
Import faqat yangilarini qo'shadi, shuning uchun qayta ishga tushirish
xavfsiz.
"""

import json
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import normalize_phone
from apps.billing.models import Branch, Student

# "Farg‘ona" / "Farg’ona" / "Farg'ona" — bir xil filial, turli tirnoq
# belgilari bilan yozilgan eski yozuvlarda. Solishtirish uchun tekislaymiz.
_APOSTROPHES = {0x2018: "'", 0x2019: "'", 0x02BC: "'", 0x02BB: "'"}


def _norm_name(name: str) -> str:
    return (name or "").translate(_APOSTROPHES).strip().lower()


class Command(BaseCommand):
    help = "Eski web tizimi dumpdata JSON'idan filial va talabalarni import qiladi"

    def add_arguments(self, parser):
        parser.add_argument("path", help="dumpdata JSON fayli")
        parser.add_argument("--dry-run", action="store_true", help="Hech narsa yozmaydi")

    def handle(self, *args, **options):
        path = Path(options["path"])
        if not path.exists():
            raise CommandError(f"Fayl topilmadi: {path}")

        data = json.loads(path.read_text(encoding="utf-8"))
        self.stats = {
            "branches_created": 0, "branches_matched": 0,
            "students_created": 0, "students_existing": 0, "students_skipped": 0,
        }
        try:
            with transaction.atomic():
                branches = self._import_branches(data)
                self._import_students(data, branches)
                if options["dry_run"]:
                    transaction.set_rollback(True)
        finally:
            if options["dry_run"]:
                self.stdout.write("--dry-run: hech narsa yozilmadi")
            for key, value in self.stats.items():
                self.stdout.write(f"{key}: {value}")

    def _import_branches(self, data) -> dict[int, Branch]:
        mapping: dict[int, Branch] = {}
        by_name = {_norm_name(b.name): b for b in Branch.objects.all()}
        for row in data:
            if row["model"] != "home.branch":
                continue
            old_id = row["pk"]
            raw_name = row["fields"].get("name") or f"Filial {old_id}"
            key = _norm_name(raw_name)
            branch = by_name.get(key)
            if branch is None:
                branch = Branch.objects.create(name=raw_name.strip())
                by_name[key] = branch
                self.stats["branches_created"] += 1
            else:
                self.stats["branches_matched"] += 1
            mapping[old_id] = branch
        return mapping

    def _import_students(self, data, branches: dict[int, Branch]) -> None:
        existing_phones = set(Student.objects.values_list("phone", flat=True))
        for row in data:
            if row["model"] != "home.student":
                continue
            f = row["fields"]
            raw_phone = f.get("phone")
            try:
                phone = normalize_phone(raw_phone)
            except ValidationError:
                self.stderr.write(
                    f"talaba {row['pk']}: '{raw_phone}' yaroqsiz raqam, o'tkazildi"
                )
                self.stats["students_skipped"] += 1
                continue

            if phone in existing_phones:
                self.stats["students_existing"] += 1
                continue

            password = (f.get("password") or "").strip()[:10] or "000000"
            hujjat = f.get("hujjat") if f.get("hujjat") in ("+", "-") else "-"
            Student.objects.create(
                name=(f.get("name") or "").strip()[:100],
                branch=branches.get(f.get("branch")),
                phone=phone,
                password=password,
                hujjat=hujjat,
                is_active=bool(f.get("is_active", True)),
                is_online=bool(f.get("is_online", False)),
            )
            existing_phones.add(phone)
            self.stats["students_created"] += 1
