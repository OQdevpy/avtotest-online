"""Learning content.

Modelled directly on the legacy `home` app of `avtotest-desktop-seoul`:

    home.oraliq                 -> Section
    home.oraliqdarslar          -> Lesson
    home.oraliqdarslarquestion  -> Question
    home.oraliqdarslaranswer    -> Answer
    question.json (var_id)      -> Ticket / TicketQuestion

Legacy column names (`name_uz`, `question_ru`, `is_true`, …) are preserved so
the fixtures import 1:1 — see `management/commands/import_seoul.py`.
"""

from django.db import models

from common.models import TimeStampedModel


class Section(models.Model):
    """A PDD chapter — legacy `home.oraliq` (4 rows in the dump)."""

    name_uz = models.CharField(max_length=255)
    name_ru = models.CharField(max_length=255, blank=True)
    name_cry = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0, db_index=True)  # legacy `tartib`
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("order", "id")
        verbose_name = "Bo'lim"
        verbose_name_plural = "Bo'limlar"

    def __str__(self) -> str:
        return self.name_uz


class Lesson(models.Model):
    """Legacy `home.oraliqdarslar` (30 rows)."""

    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="lessons")
    name_uz = models.CharField(max_length=255)
    name_ru = models.CharField(max_length=255, blank=True)
    name_cry = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("order", "id")
        verbose_name = "Dars"
        verbose_name_plural = "Darslar"

    def __str__(self) -> str:
        return self.name_uz


class PublishedQuestionManager(models.Manager):
    """Faqat nashr etilgan savollar — o'quvchiga ko'rinadigan barcha yo'llar shundan o'qiydi."""

    def get_queryset(self):
        return super().get_queryset().filter(is_published=True)


class Question(TimeStampedModel):
    """Legacy `home.oraliqdarslarquestion` (~1151 rows).

    `explanation_*` has no legacy counterpart — the mobile app shows an "Izoh"
    panel, so the columns exist but are empty until content is authored.
    """

    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="questions", null=True, blank=True
    )
    text_uz = models.TextField()
    text_ru = models.TextField(blank=True)
    text_cry = models.TextField(blank=True)
    explanation_uz = models.TextField(blank=True)
    explanation_ru = models.TextField(blank=True)
    explanation_cry = models.TextField(blank=True)
    # Legacy stores a relative path like "images/Рисунок3_2zls8vx.png".
    image = models.CharField(max_length=255, blank=True)
    # Legacy `description_image` — izoh (tushuntirish) uchun rasm.
    explanation_image = models.CharField(max_length=255, blank=True)
    # Audio izoh — media ichidagi ovozli fayl yo'li (bo'lsa karnay ikoni chiqadi).
    audio = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)
    # admin-panel'dagi maydon — web versiyada ko'rsatish belgisi.
    is_in_web = models.BooleanField(default=False, verbose_name="Webda")
    # Nashr etilmagan savol o'quvchiga hech qayerda ko'rinmaydi. Import
    # qilinganlar True (migratsiya), API orqali yangi yaratilgani False —
    # shef yarim yozilgan savolni tasodifan jonli qilib qo'ymasin.
    is_published = models.BooleanField(default=False, db_index=True,
                                       verbose_name="Nashr etilgan")

    objects = models.Manager()
    published = PublishedQuestionManager()

    class Meta:
        ordering = ("order", "id")
        verbose_name = "Savol"
        verbose_name_plural = "Savollar"
        indexes = [models.Index(fields=["lesson", "order"])]

    def __str__(self) -> str:
        return self.text_uz[:60]

    @property
    def correct_answer(self):
        return self.answers.filter(is_true=True).first()


class Answer(TimeStampedModel):
    """Legacy `home.oraliqdarslaranswer` (~3754 rows)."""

    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers")
    text_uz = models.TextField()
    text_ru = models.TextField(blank=True)
    text_cry = models.TextField(blank=True)
    is_true = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("order", "id")
        verbose_name = "Javob"
        verbose_name_plural = "Javoblar"

    def __str__(self) -> str:
        return f"{'✓' if self.is_true else '✗'} {self.text_uz[:50]}"


class Ticket(models.Model):
    """A bilet — legacy `question.json` grouped by `var_id` (57 variants × 20)."""

    number = models.PositiveIntegerField(unique=True, db_index=True)
    questions = models.ManyToManyField(
        Question, through="TicketQuestion", related_name="tickets"
    )
    # Faqat PRO obunachilarga ochiq bilet — mijozda qulf bilan ko'rsatiladi.
    is_pro = models.BooleanField(default=False, verbose_name="Faqat PRO uchun")

    class Meta:
        ordering = ("number",)
        verbose_name = "Bilet"
        verbose_name_plural = "Biletlar"

    def __str__(self) -> str:
        return f"Bilet {self.number}"


class TicketQuestion(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="items")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("order", "id")
        unique_together = ("ticket", "question")


class Blits(models.Model):
    """Blits — nomlangan savollar to'plami (admin-panel'dagi `blits.json`).

    Biletdan farqi: savollar soni erkin (odatda ~60) va to'plam shef tomonidan
    qo'lda yig'iladi, `var_id` bo'yicha avtomatik guruhlanmaydi.
    """

    name_uz = models.CharField(max_length=255)
    name_ru = models.CharField(max_length=255, blank=True)
    name_cry = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0, db_index=True)
    questions = models.ManyToManyField(
        Question, through="BlitsQuestion", related_name="blits_sets"
    )
    is_active = models.BooleanField(default=True, db_index=True, verbose_name="Faol")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("order", "id")
        verbose_name = "Blits"
        verbose_name_plural = "Blitslar"

    def __str__(self) -> str:
        return self.name_uz


class BlitsQuestion(models.Model):
    blits = models.ForeignKey(Blits, on_delete=models.CASCADE, related_name="items")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("order", "id")
        unique_together = ("blits", "question")
