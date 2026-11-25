"""Eski avtotest bazasini (avtotest-tayyorlov.uz) shu bazaga qo'shib birlashtiradi.

    python manage.py merge_legacy_db --legacy-db avtotest_legacy --dry-run
    python manage.py merge_legacy_db --legacy-db avtotest_legacy

Eski baza shu Postgres serverida alohida baza sifatida turishi kerak
(`--legacy-db` — uning nomi; foydalanuvchi va parol shu bazaniki bilan bir xil).
Boshqa joyda bo'lsa — `LEGACY_DATABASE_URL` (settings'dagi `legacy` ulanishi).

Qoidalar:

* Shu bazadagi hech narsa o'chirilmaydi va ustiga yozilmaydi — faqat qo'shiladi.
  Yagona istisno: bir xil telefonli hisobda PRO muddati uzunrog'i, rol esa
  kattarog'i olinadi, bo'sh maydonlar (filial, parol) eskisidan to'ldiriladi.
* Mos yozuvlar tabiiy kalit bilan topiladi (telefon, kod, filial nomi, bilet
  raqami, savol matni, natija vaqti) — buyruqni qayta ishga tushirish xavfsiz,
  ikki marta qo'shilmaydi. Keyinroq eski bazada paydo bo'lganlar ham qo'shiladi.
* Eski bazada bo'lib, bu yerda yo'q savollar (javoblari bilan) qo'shiladi va
  biletga joylanadi. Rasm fayllarini media papkaga alohida ko'chirish kerak.
* Qurilma sessiyalari (Device) ko'chirilmaydi — foydalanuvchi qayta kiradi.
  Bildirishnomalar ko'chirilmaydi (ikki tizimda tuzilishi har xil).
* Hammasi bitta tranzaksiyada: xato bo'lsa hech narsa yozilmaydi.
  `--dry-run` — hisoblaydi va oxirida hammasini bekor qiladi.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import timezone as dt_timezone

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connections, transaction
from django.utils import timezone

from apps.accounts.models import AccessCode, SocialAccount, User
from apps.billing.models import Branch, PaymentReport, Student, StudentPayment
from apps.content.models import (
    Answer, Blits, Lesson, Question, Section, Ticket, TicketQuestion,
)
from apps.content.tickets import TICKET_SIZE, assign_to_ticket
from apps.exams.models import ExamSession, ExamSessionQuestion
from apps.progress.models import (
    BlitsResult, ExamAttempt, LessonResult, Mistake, QuestionAttempt, SavedQuestion,
    TicketResult,
)
from apps.telegramauth.models import TelegramAccount

LEGACY = "legacy"
BATCH = 2000
ROLE_RANK = {"guest": 0, "student": 1, "teacher": 2, "admin": 3}
LANGUAGES = {"uz": "uz", "kr": "kr", "ru": "ru", "qq": "uz"}


class DryRun(Exception):
    """Sinov rejimida tranzaksiyani bekor qilish uchun."""


def norm(text) -> str:
    return " ".join((text or "").split()).lower()


def aware(value):
    if value is not None and timezone.is_naive(value):
        return timezone.make_aware(value, dt_timezone.utc)
    return value


@contextmanager
def keep_timestamps(*models):
    """auto_now/auto_now_add vaqtinchalik o'chiriladi — eski sanalar saqlansin."""
    saved = []
    for model in models:
        for field in model._meta.concrete_fields:
            if getattr(field, "auto_now", False) or getattr(field, "auto_now_add", False):
                saved.append((field, field.auto_now, field.auto_now_add))
                field.auto_now = field.auto_now_add = False
    try:
        yield
    finally:
        for field, now, now_add in saved:
            field.auto_now, field.auto_now_add = now, now_add


class Command(BaseCommand):
    help = "Eski avtotest bazasini shu bazaga qo'shib birlashtiradi (hech narsa o'chirilmaydi)"

    def add_arguments(self, parser):
        parser.add_argument("--legacy-db", default="",
                            help="Eski baza nomi (shu Postgres serverida)")
        parser.add_argument("--dry-run", action="store_true",
                            help="Faqat hisoblaydi, hech narsa yozilmaydi")
        parser.add_argument("--sync-content", action="store_true",
                            help="Ikkala bazada bir xil id va matnli mavzu/savol/javob — eski bazadagi "
                                 "tahrir olinadi (matn, tartib, rasm); savolning ortiqcha javobi o'chiriladi")
        parser.add_argument("--keep-existing-users", action="store_true",
                            help="Faqat yangi foydalanuvchi qo'shiladi; mavjudlarining roli, PRO muddati "
                                 "va boshqa maydonlari o'zgartirilmaydi")

    # --- yordamchilar ----------------------------------------------------

    def rows(self, model, where: str = "", params=()):
        """Eski bazadagi jadval qatorlari (lug'at), faqat shu modelda bor ustunlar."""
        table = model._meta.db_table
        with connections[LEGACY].cursor() as cursor:
            cursor.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
                [table],
            )
            legacy_cols = {r[0] for r in cursor.fetchall()}
        if not legacy_cols:
            return []
        cols = [f.column for f in model._meta.concrete_fields if f.column in legacy_cols]
        sql = f'SELECT {", ".join(chr(34) + c + chr(34) for c in cols)} FROM "{table}" {where} ORDER BY "id"'
        out = []
        with connections[LEGACY].cursor() as cursor:
            cursor.execute(sql, params)
            for row in cursor.fetchall():
                out.append({c: (aware(v) if hasattr(v, "tzinfo") else v)
                            for c, v in zip(cols, row)})
        return out

    def build(self, model, row, skip=("id",), **override):
        values = {k: v for k, v in row.items() if k not in skip}
        values.update(override)
        return model(**values)

    def done(self, name, count):
        self.stats[name] += count

    # --- asosiy ----------------------------------------------------------

    def handle(self, *args, legacy_db="", dry_run=False, sync_content=False,
               keep_existing_users=False, **options):
        self.keep_existing_users = keep_existing_users
        if legacy_db:
            settings.DATABASES[LEGACY] = {**settings.DATABASES["default"], "NAME": legacy_db}
        if LEGACY not in settings.DATABASES:
            raise CommandError("Eski baza ko'rsatilmagan: --legacy-db NOM yoki LEGACY_DATABASE_URL")
        if settings.DATABASES[LEGACY]["NAME"] == settings.DATABASES["default"]["NAME"]:
            raise CommandError("Eski baza va shu baza bir xil — to'xtatildi")

        self.stats = Counter()
        try:
            with transaction.atomic(), keep_timestamps(
                User, Branch, Student, StudentPayment, PaymentReport, AccessCode,
                SocialAccount, TelegramAccount, Section, Lesson, Question, Answer,
                LessonResult, TicketResult, BlitsResult, ExamAttempt, QuestionAttempt,
                SavedQuestion, Mistake, ExamSession,
            ):
                if sync_content:
                    self.sync_content()
                self.merge_content()
                self.merge_users()
                self.merge_billing()
                self.merge_codes()
                self.merge_progress()
                self.merge_exams()
                self.report(dry_run)
                if dry_run:
                    raise DryRun
        except DryRun:
            self.stdout.write(self.style.WARNING("Sinov (--dry-run): hech narsa yozilmadi."))
            return
        self.stdout.write(self.style.SUCCESS("Tayyor: eski baza qo'shildi."))

    def report(self, dry_run):
        self.stdout.write(("SINOV — " if dry_run else "") + "Qo'shildi / birlashtirildi:")
        for key in sorted(self.stats):
            self.stdout.write(f"  {key}: {self.stats[key]}")

    # --- kontent ---------------------------------------------------------

    def sync_content(self):
        """Bir xil id'li mavzu, savol va javoblarni eski bazadagidek qiladi.

        Savol bir xil hisoblanadi: id ham, matni ham (`norm`) mos. Mavzu — id va
        bo'limi mos. Javoblar shu savol ichida id bo'yicha; eski bazada shu savolda
        bo'lmagan javob o'chiriladi (natijalardagi havola NULL bo'ladi), eski bazada
        bor-u bu yerda yo'q javob qo'shiladi. Qolgan narsa `merge_content` da.
        """
        def copy(obj, row, skip):
            changed = [f.attname for f in obj._meta.concrete_fields
                       if f.attname in row and f.attname not in skip
                       and getattr(obj, f.attname) != row[f.attname]]
            for name in changed:
                setattr(obj, name, row[name])
            if changed:
                obj.save(update_fields=changed)
            return bool(changed)

        lessons = {lsn.pk: lsn for lsn in Lesson.objects.all()}
        count = 0
        for row in self.rows(Lesson):
            obj = lessons.get(row["id"])
            if obj is not None and obj.section_id == row["section_id"]:
                count += copy(obj, row, {"id", "section_id"})
        self.done("dars (eski bazadan tahrir)", count)

        questions = {q.pk: q for q in Question.objects.all()}
        same = set()
        count = 0
        for row in self.rows(Question):
            obj = questions.get(row["id"])
            if obj is None or norm(obj.text_uz) != norm(row["text_uz"]):
                continue
            if row["lesson_id"] is not None and row["lesson_id"] not in lessons:
                continue
            same.add(obj.pk)
            count += copy(obj, row, {"id", "created_at"})
        self.done("savol (eski bazadan tahrir)", count)

        legacy_answers = defaultdict(dict)
        for row in self.rows(Answer):
            if row["question_id"] in same:
                legacy_answers[row["question_id"]][row["id"]] = row
        updated = created = deleted = 0
        for a in Answer.objects.filter(question_id__in=same):
            row = legacy_answers[a.question_id].pop(a.pk, None)
            if row is None:
                a.delete()
                deleted += 1
            else:
                updated += copy(a, row, {"id", "question_id", "created_at"})
        for rows in legacy_answers.values():
            for row in rows.values():
                obj = self.build(Answer, row)
                obj.save()
                created += 1
        self.done("javob (eski bazadan tahrir)", updated)
        self.done("javob (eski bazadan qo'shildi)", created)
        self.done("javob (eski bazada yo'q — o'chirildi)", deleted)

    def merge_content(self):
        self.section = {}
        by_name = {norm(s.name_uz): s.pk for s in Section.objects.all()}
        for row in self.rows(Section):
            pk = by_name.get(norm(row["name_uz"]))
            if pk is None:
                obj = self.build(Section, row)
                obj.save()
                pk = obj.pk
                self.done("bo'lim (yangi)", 1)
            self.section[row["id"]] = pk

        self.lesson = {}
        by_name = {norm(lsn.name_uz): lsn.pk for lsn in Lesson.objects.all()}
        for row in self.rows(Lesson):
            pk = by_name.get(norm(row["name_uz"]))
            if pk is None:
                obj = self.build(Lesson, row, section_id=self.section.get(row["section_id"]))
                if hasattr(obj, "banner"):
                    obj.banner = row.get("banner", "") or ""
                obj.save()
                pk = obj.pk
                self.done("dars (yangi)", 1)
            self.lesson[row["id"]] = pk

        # Savollar: avval bir xil id va matn, keyin matn + rasm bo'yicha, bo'lmasa yangi.
        # Matn bir xil, rasmi boshqa savollar bor ("Qaysi belgilar ...?") — ular boshqa savol.
        self.question = {}
        existing = {}
        by_text = defaultdict(list)
        for q in Question.objects.only("id", "text_uz", "image"):
            existing[q.pk] = norm(q.text_uz)
            by_text[(existing[q.pk], str(q.image or ""))].append(q.pk)
        created = []
        for row in self.rows(Question):
            text = norm(row["text_uz"])
            same_text = by_text.get((text, row.get("image") or ""))
            if existing.get(row["id"]) == text:
                self.question[row["id"]] = row["id"]
            elif same_text:
                self.question[row["id"]] = same_text[0]
            else:
                obj = self.build(Question, row, lesson_id=self.lesson.get(row["lesson_id"]))
                obj.save()
                self.question[row["id"]] = obj.pk
                created.append((row["id"], obj))
        self.done("savol (yangi)", len(created))

        # Javoblar: mos savolda matn yoki tartib bo'yicha; yangi savolga yangi javob
        self.answer = {}
        new_answers = defaultdict(list)
        for a in Answer.objects.filter(question_id__in=set(self.question.values())):
            new_answers[a.question_id].append(a)
        created_ids = {old for old, _ in created}
        count = 0
        for row in self.rows(Answer):
            qid = self.question.get(row["question_id"])
            if qid is None:
                continue
            if row["question_id"] not in created_ids:
                match = next((a for a in new_answers[qid] if norm(a.text_uz) == norm(row["text_uz"])), None)
                if match is None:
                    match = next((a for a in new_answers[qid] if a.order == row["order"]), None)
                if match is not None:
                    self.answer[row["id"]] = match.pk
                    continue
            obj = self.build(Answer, row, question_id=qid)
            obj.save()
            new_answers[qid].append(obj)
            self.answer[row["id"]] = obj.pk
            count += 1
        self.done("javob (yangi)", count)

        # Biletlar: raqam bo'yicha; yangi savol eski biletiga (joy bo'lsa) yoki qoida bo'yicha
        self.ticket = {t.number: t.pk for t in Ticket.objects.all()}
        legacy_tickets = {r["id"]: r for r in self.rows(Ticket)}
        self.ticket_by_old = {}
        for old_id, row in legacy_tickets.items():
            if row["number"] not in self.ticket:
                self.ticket[row["number"]] = Ticket.objects.create(
                    number=row["number"], is_pro=row.get("is_pro", False)).pk
                self.done("bilet (yangi)", 1)
            self.ticket_by_old[old_id] = self.ticket[row["number"]]
        if created:
            placed = {r["question_id"]: r for r in self.rows(TicketQuestion)}
            for old_id, obj in created:
                if TicketQuestion.objects.filter(question=obj).exists():
                    continue
                item = placed.get(old_id)
                ticket_id = self.ticket_by_old.get(item["ticket_id"]) if item else None
                if ticket_id and TicketQuestion.objects.filter(ticket_id=ticket_id).count() < TICKET_SIZE:
                    order = TicketQuestion.objects.filter(ticket_id=ticket_id).count() + 1
                    TicketQuestion.objects.create(ticket_id=ticket_id, question=obj, order=order)
                else:
                    assign_to_ticket(obj)
            self.done("yangi savol biletga joylandi", len(created))

        self.blits = {}
        by_name = {norm(b.name_uz): b.pk for b in Blits.objects.all()}
        for row in self.rows(Blits):
            if norm(row["name_uz"]) in by_name:
                self.blits[row["id"]] = by_name[norm(row["name_uz"])]

    # --- foydalanuvchilar ------------------------------------------------

    def merge_users(self):
        self.branch = {}
        by_name = {norm(b.name): b.pk for b in Branch.objects.all()}
        for row in self.rows(Branch):
            pk = by_name.get(norm(row["name"]))
            if pk is None:
                obj = self.build(Branch, row)
                obj.save()
                pk = by_name[norm(row["name"])] = obj.pk
                self.done("filial (yangi)", 1)
            self.branch[row["id"]] = pk

        self.user = {}
        existing = {u.phone: u for u in User.objects.all()}
        created = merged = 0
        for row in self.rows(User):
            row["language"] = LANGUAGES.get(row.get("language") or "uz", "uz")
            branch_id = self.branch.get(row.get("branch_id"))
            user = existing.get(row["phone"])
            if user is None:
                user = self.build(User, row, branch_id=branch_id)
                user.save()
                existing[user.phone] = user
                created += 1
            elif not self.keep_existing_users:
                changed = self.merge_user(user, row, branch_id)
                merged += int(changed)
            self.user[row["id"]] = user.pk
        self.done("foydalanuvchi (yangi)", created)
        self.done("foydalanuvchi (mavjudi bilan birlashtirildi)", merged)

    def merge_user(self, user, row, branch_id) -> bool:
        changed = []
        if ROLE_RANK.get(row["role"], 0) > ROLE_RANK.get(user.role, 0):
            user.role = row["role"]
            changed.append("role")
        if row.get("is_pro"):
            old_until = row.get("pro_until")
            old_active = old_until is None or old_until > timezone.now()
            if old_active and (not user.pro_active or (
                    user.pro_until is not None and (old_until is None or old_until > user.pro_until))):
                user.is_pro, user.pro_until = True, old_until
                changed += ["is_pro", "pro_until"]
        if user.branch_id is None and branch_id:
            user.branch_id = branch_id
            changed.append("branch")
        if not user.has_usable_password() and row.get("password") and not row["password"].startswith("!"):
            user.password = row["password"]
            changed.append("password")
        if not user.full_name and row.get("full_name"):
            user.full_name = row["full_name"]
            changed.append("full_name")
        if row.get("date_joined") and row["date_joined"] < user.date_joined:
            user.date_joined = row["date_joined"]
            changed.append("date_joined")
        for flag in ("is_staff", "is_superuser"):
            if row.get(flag) and not getattr(user, flag):
                setattr(user, flag, True)
                changed.append(flag)
        if changed:
            user.save(update_fields=sorted(set(changed)))
        return bool(changed)

    # --- avtomaktab va to'lovlar -----------------------------------------

    def merge_billing(self):
        by_user = set(Student.objects.values_list("user_id", flat=True))
        by_phone = set(Student.objects.values_list("phone", flat=True))
        count = 0
        for row in self.rows(Student):
            uid = self.user.get(row["user_id"])
            if uid is None or uid in by_user or row["phone"] in by_phone:
                continue
            Student.objects.bulk_create([self.build(
                Student, row, user_id=uid, branch_id=self.branch.get(row.get("branch_id")))])
            by_user.add(uid)
            by_phone.add(row["phone"])
            count += 1
        self.done("avtomaktab o'quvchisi (yangi)", count)

        payment = {}
        have = {p.user_id: p.pk for p in StudentPayment.objects.all()}
        count = 0
        for row in self.rows(StudentPayment):
            uid = self.user.get(row["user_id"])
            if uid is None:
                continue
            if uid in have:
                payment[row["id"]] = (have[uid], False)
                continue
            obj = StudentPayment.objects.bulk_create([self.build(StudentPayment, row, user_id=uid)])[0]
            have[uid] = obj.pk
            payment[row["id"]] = (obj.pk, True)
            count += 1
        self.done("to'lov hisobi (yangi)", count)

        reports = []
        for row in self.rows(PaymentReport):
            target = payment.get(row["student_payment_id"])
            if target and target[1]:  # faqat yangi qo'shilgan hisobning tarixi
                reports.append(self.build(PaymentReport, row, student_payment_id=target[0]))
        PaymentReport.objects.bulk_create(reports, batch_size=BATCH)
        self.done("to'lov yozuvi (yangi)", len(reports))

    def merge_codes(self):
        have = set(AccessCode.objects.values_list("code", flat=True))
        new = []
        for row in self.rows(AccessCode):
            if row["code"] in have or self.user.get(row["user_id"]) is None:
                continue
            new.append(self.build(AccessCode, row, user_id=self.user[row["user_id"]],
                                  created_by_id=self.user.get(row.get("created_by_id"))))
            have.add(row["code"])
        AccessCode.objects.bulk_create(new, batch_size=BATCH)
        self.done("kirish kodi (yangi)", len(new))

        have = set(SocialAccount.objects.values_list("provider", "uid"))
        new = [self.build(SocialAccount, r, user_id=self.user[r["user_id"]])
               for r in self.rows(SocialAccount)
               if (r["provider"], r["uid"]) not in have and r["user_id"] in self.user]
        SocialAccount.objects.bulk_create(new, batch_size=BATCH)
        self.done("Apple/Google hisobi (yangi)", len(new))

        have = set(TelegramAccount.objects.values_list("telegram_id", flat=True))
        phone_user = dict(User.objects.values_list("phone", "id"))
        new = [self.build(TelegramAccount, r, user_id=phone_user.get(r["phone"]))
               for r in self.rows(TelegramAccount) if r["telegram_id"] not in have]
        TelegramAccount.objects.bulk_create(new, batch_size=BATCH)
        self.done("Telegram bog'lanishi (yangi)", len(new))

    # --- natijalar -------------------------------------------------------

    def copy_results(self, model, fk: str, mapping: dict, label: str):
        """Natija tarixi: (foydalanuvchi, obyekt, vaqt) bir xil bo'lsa — bor deb hisoblanadi."""
        fk_id = f"{fk}_id"
        users = set(self.user.values())
        have = set(model.objects.filter(user_id__in=users)
                   .values_list("user_id", fk_id, "created_at"))
        new = []
        for row in self.rows(model):
            uid, target = self.user.get(row["user_id"]), mapping.get(row[fk_id])
            if uid is None or target is None or (uid, target, row["created_at"]) in have:
                continue
            new.append(self.build(model, row, user_id=uid, **{fk_id: target}))
        model.objects.bulk_create(new, batch_size=BATCH)
        self.done(label, len(new))

    def merge_progress(self):
        self.copy_results(LessonResult, "lesson", self.lesson, "dars natijasi")
        self.copy_results(TicketResult, "ticket", self.ticket_by_old, "bilet natijasi")
        self.copy_results(BlitsResult, "blits", self.blits, "blits natijasi")

        users = set(self.user.values())
        have = set(QuestionAttempt.objects.filter(user_id__in=users)
                   .values_list("user_id", "question_id", "created_at"))
        new = []
        for row in self.rows(QuestionAttempt):
            uid, qid = self.user.get(row["user_id"]), self.question.get(row["question_id"])
            if uid is None or qid is None or (uid, qid, row["created_at"]) in have:
                continue
            new.append(self.build(QuestionAttempt, row, user_id=uid, question_id=qid,
                                  answer_id=self.answer.get(row.get("answer_id"))))
            if len(new) >= BATCH:
                QuestionAttempt.objects.bulk_create(new)
                self.done("savolga javob tarixi", len(new))
                new = []
        QuestionAttempt.objects.bulk_create(new)
        self.done("savolga javob tarixi", len(new))

        have = set(SavedQuestion.objects.filter(user_id__in=users).values_list("user_id", "question_id"))
        new = []
        for row in self.rows(SavedQuestion):
            key = (self.user.get(row["user_id"]), self.question.get(row["question_id"]))
            if None in key or key in have:
                continue
            have.add(key)
            new.append(self.build(SavedQuestion, row, user_id=key[0], question_id=key[1]))
        SavedQuestion.objects.bulk_create(new, batch_size=BATCH)
        self.done("sevimli savol", len(new))

        mistakes = {(m.user_id, m.question_id): m for m in Mistake.objects.filter(user_id__in=users)}
        new, updated = [], 0
        for row in self.rows(Mistake):
            key = (self.user.get(row["user_id"]), self.question.get(row["question_id"]))
            if None in key:
                continue
            current = mistakes.get(key)
            if current is None:
                obj = self.build(Mistake, row, user_id=key[0], question_id=key[1],
                                 last_wrong_answer_id=self.answer.get(row.get("last_wrong_answer_id")))
                mistakes[key] = obj
                new.append(obj)
            elif current.pk and (row["wrong_count"] > current.wrong_count
                                 or (current.resolved and not row["resolved"])):
                # Bir xil xato ikkala tizimda: kattaroq hisob, hal qilinmagani ustun
                current.wrong_count = max(current.wrong_count, row["wrong_count"])
                current.resolved = current.resolved and row["resolved"]
                current.save(update_fields=["wrong_count", "resolved"])
                updated += 1
        Mistake.objects.bulk_create(new, batch_size=BATCH)
        self.done("xato (yangi)", len(new))
        self.done("xato (birlashtirildi)", updated)

        self.attempt = {}
        have = {(a.user_id, a.created_at): a.pk for a in ExamAttempt.objects.filter(user_id__in=users)}
        count = 0
        for row in self.rows(ExamAttempt):
            uid = self.user.get(row["user_id"])
            if uid is None:
                continue
            key = (uid, row["created_at"])
            if key not in have:
                obj = self.build(ExamAttempt, row, user_id=uid)
                obj.save()
                have[key] = obj.pk
                count += 1
            self.attempt[row["id"]] = have[key]
        self.done("imtihon natijasi", count)

    def merge_exams(self):
        users = set(self.user.values())
        have = {(s.user_id, s.started_at) for s in ExamSession.objects.filter(user_id__in=users)}
        session = {}
        count = 0
        for row in self.rows(ExamSession):
            uid = self.user.get(row["user_id"])
            if uid is None or (uid, row["started_at"]) in have:
                continue
            attempt = self.attempt.get(row.get("attempt_id"))
            if attempt and ExamSession.objects.filter(attempt_id=attempt).exists():
                attempt = None
            obj = self.build(ExamSession, row, user_id=uid, attempt_id=attempt)
            obj.save()
            session[row["id"]] = obj.pk
            count += 1
        self.done("imtihon sessiyasi", count)
        if not session:
            return
        new, seen = [], set()
        for row in self.rows(ExamSessionQuestion):
            sid, qid = session.get(row["session_id"]), self.question.get(row["question_id"])
            if sid is None or qid is None or (sid, qid) in seen:
                continue
            seen.add((sid, qid))
            new.append(self.build(ExamSessionQuestion, row, session_id=sid, question_id=qid,
                                  answer_id=self.answer.get(row.get("answer_id"))))
        ExamSessionQuestion.objects.bulk_create(new, batch_size=BATCH)
        self.done("imtihon savoli", len(new))
