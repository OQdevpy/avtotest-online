from django.db import models

class Section(models.Model):
    name_uz = models.CharField(max_length=255)
    name_ru = models.CharField(max_length=255, blank=True)
    name_cry = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("order", "id")
        verbose_name = "Bo'lim"
        verbose_name_plural = "Bo'limlar"

    def __str__(self) -> str:
        return self.name_uz

class Lesson(models.Model):
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


class Question(models.Model):
    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="questions", null=True, blank=True
    )
    text_uz = models.TextField()
    text_ru = models.TextField(blank=True)
    text_cry = models.TextField(blank=True)
    explanation_uz = models.TextField(blank=True)
    explanation_ru = models.TextField(blank=True)
    explanation_cry = models.TextField(blank=True)
    image = models.CharField(max_length=255, blank=True)
    explanation_image = models.CharField(max_length=255, blank=True)
    audio = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("order", "id")
        verbose_name = "Savol"
        verbose_name_plural = "Savollar"
        indexes = [models.Index(fields=["lesson", "order"])]

    def __str__(self) -> str:
        return self.text_uz[:60]


class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers")
    text_uz = models.TextField()
    text_ru = models.TextField(blank=True)
    text_cry = models.TextField(blank=True)
    is_true = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("order", "id")
        verbose_name = "Javob"
        verbose_name_plural = "Javoblar"

    def __str__(self) -> str:
        return f"{'✓' if self.is_true else '✗'} {self.text_uz[:50]}"


class Ticket(models.Model):
    number = models.PositiveIntegerField(unique=True, db_index=True)
    questions = models.ManyToManyField(
        Question, through="TicketQuestion", related_name="tickets"
    )
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
