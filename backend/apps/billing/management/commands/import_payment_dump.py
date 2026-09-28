"""Eski web tizimi eksportidan (`dumpdata` JSON) to'lov va to'lov hisobotlarini ko'chiradi.

    python manage.py import_payment_dump /yo'l/barcha_malumotlar.json [--dry-run]

Avval `import_student_dump` mantig'i bilan filial va talabalar (yo'q bo'lsa)
yaratiladi — to'lov talabaning `User`iga bog'lanadi (`Student.user`), shuning
uchun talaba bo'lishi shart. Talabalar allaqachon mavjud bo'lsa tegilmaydi.

**Mavjud yozuv qoidasi.** Foydalanuvchida to'lov allaqachon bo'lsa, u qayta
yozilmaydi — importdan keyin qabul qilingan to'lovlar orqaga qaytmasligi
kerak. Hisobotlar eski qator id'si bo'yicha (`[web#id]` belgisi) takrorlanmaydi.

`tolagani` eski bazadan tayyor holda keladi (hisobotlar yig'indisiga teng
emas — eski to'lovlarning ko'pida hisobot yo'q), shuning uchun hisobot
saqlanganda balans qayta oshirilmaydi (`skip_balance=True`).
"""

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import normalize_phone
from apps.billing.models import PaymentReport, Student, StudentPayment

from .import_student_dump import Command as StudentDumpCommand


def money(value) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except InvalidOperation:
        return Decimal("0")


class Command(BaseCommand):
    help = "Eski web tizimi dumpdata JSON'idan to'lov va hisobotlarni import qiladi"

    def add_arguments(self, parser):
        parser.add_argument("path", help="dumpdata JSON fayli")
        parser.add_argument("--dry-run", action="store_true", help="Hech narsa yozmaydi")

    def handle(self, *args, **options):
        path = Path(options["path"])
        if not path.exists():
            raise CommandError(f"Fayl topilmadi: {path}")

        data = json.loads(path.read_text(encoding="utf-8"))
        self.stats = {
            "students_created": 0, "payments_created": 0, "payments_existing": 0,
            "payments_skipped": 0, "reports_created": 0, "reports_existing": 0,
            "reports_skipped": 0,
        }
        try:
            with transaction.atomic():
                users = self._ensure_students(data)
                payments = self._import_payments(data, users)
                self._import_reports(data, payments)
                if options["dry_run"]:
                    transaction.set_rollback(True)
        finally:
            if options["dry_run"]:
                self.stdout.write("--dry-run: hech narsa yozilmadi")
            for key, value in self.stats.items():
                self.stdout.write(f"{key}: {value}")

    def _ensure_students(self, data) -> dict:
        """Eski talaba id -> User. Yo'q talabalar dumpdan yaratiladi."""
        helper = StudentDumpCommand(stdout=self.stdout, stderr=self.stderr)
        helper.stats = {
            "branches_created": 0, "branches_matched": 0,
            "students_created": 0, "students_existing": 0, "students_skipped": 0,
        }
        helper._import_students(data, helper._import_branches(data))
        self.stats["students_created"] = helper.stats["students_created"]

        users = {}
        for row in data:
            if row["model"] != "home.student":
                continue
            try:
                phone = normalize_phone(row["fields"].get("phone"))
            except ValidationError:
                continue
            student = Student.objects.select_related("user").filter(phone=phone).first()
            if student is not None and student.user is not None:
                users[row["pk"]] = student.user
        return users

    def _import_payments(self, data, users) -> dict[int, StudentPayment]:
        mapping = {}
        for row in data:
            if row["model"] != "home.studentpayment":
                continue
            f = row["fields"]
            user = users.get(f.get("student"))
            if user is None:
                self.stderr.write(f"to'lov {row['pk']}: talaba topilmadi, o'tkazildi")
                self.stats["payments_skipped"] += 1
                continue
            # `get_or_create` — `update_or_create` emas: qayta ishga tushirish
            # importdan keyin qabul qilingan to'lovni orqaga qaytarmasin.
            payment, created = StudentPayment.objects.get_or_create(
                user=user,
                defaults={"amount": money(f.get("amount")), "tolagani": money(f.get("tolagani"))},
            )
            mapping[row["pk"]] = payment
            self.stats["payments_created" if created else "payments_existing"] += 1
        return mapping

    def _import_reports(self, data, payments) -> None:
        for row in data:
            if row["model"] != "home.paymentreport":
                continue
            f = row["fields"]
            payment = payments.get(f.get("student_payment"))
            if payment is None:
                self.stats["reports_skipped"] += 1
                continue
            # Takroriy importni eski qator id'si bo'yicha aniqlaymiz (summa va
            # sana bo'yicha emas: bir kunda bir xil summani ikki marta to'lagan
            # talabaning bitta hisoboti yo'qolardi).
            marker = f"[web#{row['pk']}]"
            if PaymentReport.objects.filter(comment__startswith=marker).exists():
                self.stats["reports_existing"] += 1
                continue
            comment = f.get("comment") or ""
            report = PaymentReport(
                student_payment=payment,
                paid_amount=money(f.get("paid_amount")),
                date=f["date"],
                comment=f"{marker} {comment}".strip(),
            )
            report.save(skip_balance=True)
            self.stats["reports_created"] += 1
