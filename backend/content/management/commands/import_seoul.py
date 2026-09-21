import json
from collections import defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from content.models import Answer, Lesson, Question, Section, Ticket, TicketQuestion

QUESTION_FILES = (
    "oraliqdarslarquestion.json",
    "new_question.json",
    "blitsquestion.json",
    "blitsquestion2.json",
    "blitsquestion3.json",
)
ANSWER_FILES = ("oraliqdarslaranswer.json", "answer.json")


def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def legacy_pk(row: dict):
    return row.get("id", row.get("pk"))


class Command(BaseCommand):
    help = "avtotest-desktop-seoul fixture'larini import qiladi"

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            required=True,
            help="`src/db` papkasiga yo'l (avtotest-desktop-seoul reposidan)",
        )
        parser.add_argument(
            "--skip-tickets",
            action="store_true",
            help="question.json (biletlar) importini o'tkazib yuborish",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        base = Path(options["path"]).expanduser().resolve()
        if not base.is_dir():
            raise CommandError(f"Papka topilmadi: {base}")

        self.stdout.write(self.style.MIGRATE_HEADING(f"Manba: {base}"))

        self._import_sections(base)
        self._import_lessons(base)
        self._import_questions(base)
        self._import_answers(base)
        if not options["skip_tickets"]:
            self._import_tickets(base)

        self.stdout.write(self.style.SUCCESS("\nImport yakunlandi."))
        self.stdout.write(
            f"  Bo'limlar: {Section.objects.count()}\n"
            f"  Darslar:   {Lesson.objects.count()}\n"
            f"  Savollar:  {Question.objects.count()}\n"
            f"  Javoblar:  {Answer.objects.count()}\n"
            f"  Biletlar:  {Ticket.objects.count()}"
        )

    # --- steps --------------------------------------------------------------

    def _import_sections(self, base: Path):
        rows = load(base / "oraliq.json")
        for row in rows:
            Section.objects.update_or_create(
                id=legacy_pk(row),
                defaults={
                    "name_uz": row.get("name_uz", ""),
                    "name_ru": row.get("name_ru", ""),
                    "name_cry": row.get("name_cry", ""),
                    "order": row.get("tartib", 0) or 0,
                },
            )
        self.stdout.write(f"  oraliq.json -> {len(rows)} bo'lim")

    def _import_lessons(self, base: Path):
        rows = load(base / "oraliqdarslar.json")
        known_sections = set(Section.objects.values_list("id", flat=True))
        created = skipped = 0
        for order, row in enumerate(rows, start=1):
            section_id = row.get("oraliq")
            if section_id not in known_sections:
                skipped += 1
                continue
            Lesson.objects.update_or_create(
                id=legacy_pk(row),
                defaults={
                    "section_id": section_id,
                    "name_uz": row.get("name_uz", ""),
                    "name_ru": row.get("name_ru", ""),
                    "name_cry": row.get("name_cry", ""),
                    "order": order,
                },
            )
            created += 1
        self.stdout.write(f"  oraliqdarslar.json -> {created} dars (o'tkazib yuborildi: {skipped})")

    def _import_questions(self, base: Path):
        known_lessons = set(Lesson.objects.values_list("id", flat=True))
        seen: set[int] = set()
        total = 0
        for name in QUESTION_FILES:
            rows = load(base / name)
            for row in rows:
                pk = legacy_pk(row)
                if pk in seen:
                    continue
                seen.add(pk)
                lesson_id = row.get("oraliq_dars")
                Question.objects.update_or_create(
                    id=pk,
                    defaults={
                        "lesson_id": lesson_id if lesson_id in known_lessons else None,
                        "text_uz": row.get("question_uz", ""),
                        "text_ru": row.get("question_ru", ""),
                        "text_cry": row.get("question_cry", ""),
                        "image": row.get("image", "") or "",
                        "explanation_image": row.get("description_image", "") or "",
                        "audio": row.get("audio", "") or "",
                    },
                )
                total += 1
            self.stdout.write(f"  {name} -> {len(rows)} qator")
        self.stdout.write(f"  jami noyob savollar: {total}")

    def _import_answers(self, base: Path):
        known_questions = set(Question.objects.values_list("id", flat=True))
        seen: set[int] = set()
        order_by_question: dict[int, int] = defaultdict(int)
        total = skipped = 0
        for name in ANSWER_FILES:
            rows = load(base / name)
            for row in rows:
                pk = legacy_pk(row)
                if pk in seen:
                    continue
                seen.add(pk)
                question_id = row.get("oraliq_dars_question")
                if question_id not in known_questions:
                    skipped += 1
                    continue
                order_by_question[question_id] += 1
                Answer.objects.update_or_create(
                    id=pk,
                    defaults={
                        "question_id": question_id,
                        "text_uz": row.get("answer_uz", ""),
                        "text_ru": row.get("answer_ru", ""),
                        "text_cry": row.get("answer_cry", ""),
                        "is_true": bool(row.get("is_true")),
                        "order": order_by_question[question_id],
                    },
                )
                total += 1
            self.stdout.write(f"  {name} -> {len(rows)} qator")
        self.stdout.write(
            f"  jami noyob javoblar: {total} (savoli yo'q: {skipped})"
        )

    def _import_tickets(self, base: Path):
        rows = load(base / "question.json")
        if not rows:
            self.stdout.write("  question.json topilmadi — biletlar o'tkazib yuborildi")
            return

        known_questions = set(Question.objects.values_list("id", flat=True))
        made = 0
        for variant in rows:
            number = variant.get("var_id")
            if number is None:
                continue
            ticket, _ = Ticket.objects.update_or_create(number=number + 1)
            TicketQuestion.objects.filter(ticket=ticket).delete()
            items = []
            for order, q in enumerate(variant.get("data", []), start=1):
                qid = legacy_pk(q)
                if qid in known_questions:
                    items.append(TicketQuestion(ticket=ticket, question_id=qid, order=order))
            TicketQuestion.objects.bulk_create(items, ignore_conflicts=True)
            made += 1
        self.stdout.write(f"  question.json -> {made} bilet")
