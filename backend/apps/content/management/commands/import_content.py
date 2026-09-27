"""admin-panel JSON fayllaridan kontentni import qiladi (spec §10, 2-qadam).

Moslashtirish **id bo'yicha**: `import_seoul` legacy PK'larni saqlagan, shuning
uchun admin-panel id'lari baza id'lari bilan bir xil (savol 55 → dars 16).
Bazada bor-u JSON'da yo'q yozuv **o'chirilmaydi** — faqat hisobotda ko'rsatiladi.

    python manage.py import_content --path ../../admin-panel/src/db [--dry-run]
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.content.models import (
    Answer,
    Blits,
    BlitsQuestion,
    Lesson,
    Question,
    Section,
    Ticket,
    TicketQuestion,
)

REQUIRED_FILES = ("sections.json", "lessons.json", "questions.json", "answers.json")
OPTIONAL_FILES = ("blits.json", "variants.json")


def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


class Command(BaseCommand):
    help = "admin-panel/src/db JSON fayllaridan kontentni import qiladi"

    def add_arguments(self, parser):
        parser.add_argument("--path", required=True, help="admin-panel/src/db papkasi")
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Nima o'zgarishini ko'rsatadi, hech narsa yozmaydi",
        )

    def handle(self, *args, **options):
        base = Path(options["path"]).expanduser().resolve()
        if not base.is_dir():
            raise CommandError(f"Papka topilmadi: {base}")

        missing = [name for name in REQUIRED_FILES if not (base / name).exists()]
        if missing:
            raise CommandError(f"Majburiy fayllar topilmadi: {', '.join(missing)}")

        self.report: dict[str, dict[str, int]] = {}
        try:
            with transaction.atomic():
                self._import_sections(load(base / "sections.json"))
                self._import_lessons(load(base / "lessons.json"))
                self._import_questions(load(base / "questions.json"))
                self._import_answers(load(base / "answers.json"))
                self._import_blits(load(base / "blits.json"))
                self._import_variants(load(base / "variants.json"))
                self._report_orphans()
                if options["dry_run"]:
                    transaction.set_rollback(True)
        finally:
            self._print_report(dry_run=options["dry_run"])

    # --- yordamchilar -------------------------------------------------------

    def _count(self, model: str, key: str) -> None:
        self.report.setdefault(model, {"yaratildi": 0, "yangilandi": 0, "o'zgarmadi": 0})
        self.report[model][key] += 1

    def _upsert(self, model_cls, name: str, pk, fields: dict) -> None:
        """id bo'yicha yaratadi yoki yangilaydi; farq bo'lmasa tegmaydi."""
        existing = model_cls.objects.filter(pk=pk).first()
        if existing is None:
            model_cls.objects.create(pk=pk, **fields)
            self._count(name, "yaratildi")
            return

        changed = [
            field for field, value in fields.items()
            if getattr(existing, field) != value
        ]
        if not changed:
            self._count(name, "o'zgarmadi")
            return
        for field in changed:
            setattr(existing, field, fields[field])
        existing.save(update_fields=changed)
        self._count(name, "yangilandi")

    # --- importlar ----------------------------------------------------------

    def _import_sections(self, rows: list[dict]) -> None:
        for row in rows:
            self._upsert(Section, "sections", row["id"], {
                "name_uz": row.get("name_uz", ""),
                "name_ru": row.get("name_ru", ""),
                "name_cry": row.get("name_cry", ""),
                "order": row.get("tartib", 0),
            })

    def _import_lessons(self, rows: list[dict]) -> None:
        known = set(Section.objects.values_list("pk", flat=True))
        for row in rows:
            if row.get("section_id") not in known:
                self.stderr.write(
                    f"dars {row['id']}: bo'lim {row.get('section_id')} topilmadi, o'tkazildi"
                )
                continue
            self._upsert(Lesson, "lessons", row["id"], {
                "section_id": row["section_id"],
                "name_uz": row.get("name_uz", ""),
                "name_ru": row.get("name_ru", ""),
                "name_cry": row.get("name_cry", ""),
                "order": row.get("tartib", 0),
            })

    def _import_questions(self, rows: list[dict]) -> None:
        known = set(Lesson.objects.values_list("pk", flat=True))
        for row in rows:
            lesson_id = row.get("lesson_id")
            if lesson_id is not None and lesson_id not in known:
                self.stderr.write(
                    f"savol {row['id']}: dars {lesson_id} topilmadi, o'tkazildi"
                )
                continue
            self._upsert(Question, "questions", row["id"], {
                "lesson_id": lesson_id,
                "text_uz": row.get("question_uz", ""),
                "text_ru": row.get("question_ru", ""),
                "text_cry": row.get("question_cry", ""),
                "image": row.get("image", "") or "",
                "explanation_image": row.get("description_image", "") or "",
                "order": row.get("tartib", 0),
                "is_in_web": bool(row.get("is_in_web", False)),
                # Import — jonli kontent, shuning uchun nashr etilgan.
                "is_published": True,
            })

    def _import_answers(self, rows: list[dict]) -> None:
        known = set(Question.objects.values_list("pk", flat=True))
        for index, row in enumerate(rows):
            if row.get("question_id") not in known:
                self.stderr.write(
                    f"javob {row['id']}: savol {row.get('question_id')} topilmadi, o'tkazildi"
                )
                continue
            self._upsert(Answer, "answers", row["id"], {
                "question_id": row["question_id"],
                "text_uz": row.get("answer_uz", ""),
                "text_ru": row.get("answer_ru", ""),
                "text_cry": row.get("answer_cry", ""),
                "is_true": bool(row.get("is_true", False)),
                "order": row.get("tartib", index),
            })

    def _import_blits(self, rows: list[dict]) -> None:
        known = set(Question.objects.values_list("pk", flat=True))
        for position, row in enumerate(rows, start=1):
            self._upsert(Blits, "blits", row["id"], {
                "name_uz": row.get("name_uz", ""),
                "name_ru": row.get("name_ru", ""),
                "name_cry": row.get("name_cry", ""),
                "order": row.get("tartib", position),
            })
            self._sync_through(
                BlitsQuestion, "blits", row["id"], row.get("question_ids", []), known
            )

    def _import_variants(self, rows: list[dict]) -> None:
        """`variants.json` → `Ticket`. Variant va bilet bir xil narsa (spec §5.2).

        Eksport shakli bir xil emas: eski `id`, ba'zan `number`, yangisida
        `var_id` (0 dan boshlanadi — bilet raqami undan 1 katta).
        """
        known = set(Question.objects.values_list("pk", flat=True))
        for row in rows:
            if "number" in row:
                number = row["number"]
            elif "var_id" in row:
                number = row["var_id"] + 1
            else:
                number = row["id"]
            ticket, created = Ticket.objects.get_or_create(number=number)
            self._count("tickets", "yaratildi" if created else "o'zgarmadi")
            self._sync_through(
                TicketQuestion, "ticket", ticket.pk, row.get("question_ids", []), known
            )

    def _sync_through(self, through_cls, fk: str, parent_pk, question_ids, known) -> None:
        """M2M tartibini JSON bilan tenglashtiradi (ortiqchasi olib tashlanadi)."""
        wanted = [qid for qid in question_ids if qid in known]
        through_cls.objects.filter(**{f"{fk}_id": parent_pk}).exclude(
            question_id__in=wanted
        ).delete()
        existing = {
            obj.question_id: obj
            for obj in through_cls.objects.filter(**{f"{fk}_id": parent_pk})
        }
        to_create, to_update = [], []
        for order, qid in enumerate(wanted):
            obj = existing.get(qid)
            if obj is None:
                to_create.append(
                    through_cls(**{f"{fk}_id": parent_pk}, question_id=qid, order=order)
                )
            elif obj.order != order:
                obj.order = order
                to_update.append(obj)
        through_cls.objects.bulk_create(to_create)
        if to_update:
            through_cls.objects.bulk_update(to_update, ["order"])

    def _report_orphans(self) -> None:
        """JSON'da yo'q, bazada bor yozuvlar — o'chirilmaydi, faqat hisobot."""
        self.orphans = {
            "questions": Question.objects.count()
            - sum(self.report.get("questions", {}).values()),
            "answers": Answer.objects.count()
            - sum(self.report.get("answers", {}).values()),
        }

    def _print_report(self, *, dry_run: bool) -> None:
        if dry_run:
            self.stdout.write("--dry-run: hech narsa yozilmadi")
        for model, stats in self.report.items():
            summary = ", ".join(f"{key}: {value}" for key, value in stats.items())
            self.stdout.write(f"{model}: {summary}")
        for model, count in getattr(self, "orphans", {}).items():
            if count > 0:
                self.stdout.write(f"{model}: JSON'da yo'q, bazada qoldi: {count}")
