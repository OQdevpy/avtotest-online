"""Imtihon sessiyasi — server tomonda yuritiladigan urinish.

Eski `exam/generate/` savollarni berardi-yu, server qaysi savollar berilganini
va vaqt qachon tugashini eslamasdi. `ExamSession` shuni yozib qo'yadi: savollar
ro'yxati, boshlanish va tugash vaqti, har bir javob. Yakunda server o'zi
baholaydi va `progress.ExamAttempt` natija yozuvini yaratadi.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.content.models import Answer, Question


class ExamSession(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="exam_sessions"
    )
    mode = models.PositiveSmallIntegerField(verbose_name="Rejim (20/50)")
    started_at = models.DateTimeField(auto_now_add=True, db_index=True)
    ends_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    score = models.PositiveIntegerField(default=0)
    pass_score = models.PositiveIntegerField()
    attempt = models.OneToOneField(
        "progress.ExamAttempt", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="session",
    )

    class Meta:
        ordering = ("-started_at",)
        indexes = [models.Index(fields=["user", "-started_at"])]
        verbose_name = "Imtihon sessiyasi"
        verbose_name_plural = "Imtihon sessiyalari"

    def __str__(self) -> str:
        return f"{self.user_id} · {self.mode} · {self.score}/{self.total}"

    @property
    def total(self) -> int:
        return self.items.count()

    @property
    def is_open(self) -> bool:
        """Javob qabul qilinadimi — yakunlanmagan va vaqti tugamagan."""
        return self.finished_at is None and self.ends_at > timezone.now()

    @property
    def passed(self) -> bool:
        return self.score >= self.pass_score


class ExamSessionQuestion(models.Model):
    session = models.ForeignKey(
        ExamSession, on_delete=models.CASCADE, related_name="items"
    )
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)
    answer = models.ForeignKey(
        Answer, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    # Yakunlanmagunicha null — javob berilgani baholashdan oldin belgilanmaydi.
    is_correct = models.BooleanField(null=True, blank=True)

    class Meta:
        ordering = ("order", "id")
        unique_together = ("session", "question")
