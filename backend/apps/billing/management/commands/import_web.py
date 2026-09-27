"""Eski `web/backend` bazasidan foydalanuvchi va to'lovlarni ko'chiradi.

Eski sxema boshqa Django loyihasiga tegishli, shuning uchun ORM emas —
to'g'ridan-to'g'ri SQL o'qiladi.

    python manage.py import_web --database-url postgresql://... [--dry-run]

**Mavjud foydalanuvchi qoidasi.** Telefon bo'yicha `User` topilsa, uning
paroli, ismi va progressi **tegilmaydi** — faqat bo'sh maydonlar (`branch`,
`hujjat`) to'ldiriladi. Web'dagi parollar ochiq matnda saqlangan; yangi
foydalanuvchi uchun `set_password` bilan hash qilinadi.
"""

import sqlite3
from contextlib import closing
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import unquote, urlparse

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import User, normalize_phone
from apps.billing.models import Branch, PaymentReport, StudentPayment


def connect(url: str):
    """Eski bazaga ulanish. sqlite va postgresql qo'llanadi."""
    parsed = urlparse(url)
    scheme = parsed.scheme.split("+")[0]

    if scheme in ("sqlite", "sqlite3"):
        # Django konventsiyasi: sqlite:///nisbiy/yo'l, sqlite:////mutlaq/yo'l
        raw = unquote(parsed.path)
        path = Path(raw[1:] if raw.startswith("/") else raw)
        if not path.exists():
            raise CommandError(f"Baza fayli topilmadi: {path}")
        return sqlite3.connect(path)

    if scheme in ("postgres", "postgresql"):
        try:
            import psycopg
        except ImportError as exc:  # pragma: no cover
            raise CommandError("psycopg o'rnatilmagan") from exc
        return psycopg.connect(url)

    raise CommandError(f"Qo'llab-quvvatlanmaydigan sxema: '{scheme}'")


def rows(connection, sql: str) -> list[tuple]:
    with closing(connection.cursor()) as cursor:
        cursor.execute(sql)
        return cursor.fetchall()


def money(value) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except InvalidOperation:
        return Decimal("0")


class Command(BaseCommand):
    help = "Eski web bazasidan filial, o'quvchi va to'lovlarni import qiladi"

    def add_arguments(self, parser):
        parser.add_argument("--database-url", required=True,
                            help="Eski web bazasining manzili")
        parser.add_argument("--dry-run", action="store_true",
                            help="Hech narsa yozmaydi")

    def handle(self, *args, **options):
        connection = connect(options["database_url"])
        self.stats = {
            "branches": 0, "users_created": 0, "users_linked": 0, "users_skipped": 0,
            "payments": 0, "reports": 0,
        }
        try:
            with transaction.atomic():
                branches = self._import_branches(connection)
                users = self._import_students(connection, branches)
                payments = self._import_payments(connection, users)
                self._import_reports(connection, payments)
                if options["dry_run"]:
                    transaction.set_rollback(True)
        finally:
            connection.close()
            if options["dry_run"]:
                self.stdout.write("--dry-run: hech narsa yozilmadi")
            for key, value in self.stats.items():
                self.stdout.write(f"{key}: {value}")

    # --- qadamlar -----------------------------------------------------------

    def _import_branches(self, connection) -> dict[int, Branch]:
        mapping = {}
        for old_id, name in rows(connection, "SELECT id, name FROM home_branch"):
            branch, created = Branch.objects.get_or_create(name=name or f"Filial {old_id}")
            mapping[old_id] = branch
            if created:
                self.stats["branches"] += 1
        return mapping

    def _import_students(self, connection, branches) -> dict[int, User]:
        mapping = {}
        query = (
            "SELECT id, name, branch_id, phone, password, hujjat, is_active "
            "FROM home_student"
        )
        for old_id, name, branch_id, phone, password, hujjat, is_active in rows(
            connection, query
        ):
            try:
                normalized = normalize_phone(phone)
            except ValidationError:
                self.stderr.write(f"o'quvchi {old_id}: '{phone}' yaroqsiz raqam, o'tkazildi")
                self.stats["users_skipped"] += 1
                continue

            branch = branches.get(branch_id)
            existing = User.objects.filter(phone=normalized).first()
            if existing is not None:
                # Parol, ism va progress tegilmaydi — faqat bo'sh maydonlar.
                changed = []
                if existing.branch_id is None and branch is not None:
                    existing.branch = branch
                    changed.append("branch")
                if existing.hujjat in ("", "-") and hujjat in ("+", "-"):
                    existing.hujjat = hujjat
                    changed.append("hujjat")
                if changed:
                    existing.save(update_fields=changed)
                mapping[old_id] = existing
                self.stats["users_linked"] += 1
                continue

            user = User(
                phone=normalized,
                full_name=name or "",
                role=User.Role.STUDENT,
                branch=branch,
                hujjat=hujjat if hujjat in ("+", "-") else "-",
                is_active=bool(is_active),
            )
            if password:
                user.set_password(password)
            else:
                user.set_unusable_password()
            user.save()
            mapping[old_id] = user
            self.stats["users_created"] += 1
        return mapping

    def _import_payments(self, connection, users) -> dict[int, StudentPayment]:
        mapping = {}
        query = "SELECT id, student_id, amount, tolagani FROM home_studentpayment"
        for old_id, student_id, amount, tolagani in rows(connection, query):
            user = users.get(student_id)
            if user is None:
                continue
            payment, created = StudentPayment.objects.update_or_create(
                user=user,
                defaults={"amount": money(amount), "tolagani": money(tolagani)},
            )
            mapping[old_id] = payment
            if created:
                self.stats["payments"] += 1
        return mapping

    def _import_reports(self, connection, payments) -> None:
        """Hisobotlarni ko'chiradi.

        `tolagani` eski bazadan tayyor holda keladi, shuning uchun bu yerda
        `PaymentReport.save()` ning avtomatik oshirishi chetlab o'tiladi —
        aks holda summa ikki hisoblanardi.
        """
        query = (
            "SELECT id, student_payment_id, paid_amount, date, comment "
            "FROM home_paymentreport"
        )
        for old_id, payment_id, paid_amount, date, comment in rows(connection, query):
            payment = payments.get(payment_id)
            if payment is None:
                continue
            exists = PaymentReport.objects.filter(
                student_payment=payment, date=date, paid_amount=money(paid_amount)
            ).exists()
            if exists:
                continue
            report = PaymentReport(
                student_payment=payment,
                paid_amount=money(paid_amount),
                date=date,
                comment=comment or "",
            )
            # `_state.adding` ni saqlab qolmasdan to'g'ridan-to'g'ri INSERT —
            # `tolagani` qayta oshmasin.
            super(PaymentReport, report).save(force_insert=True)
            self.stats["reports"] += 1
