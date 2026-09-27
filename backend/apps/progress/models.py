"""User progress: lesson results, exam attempts and mistake tracking.

Replaces the mobile app's local `maxScores` map in AsyncStorage, so progress
follows the user across devices.
"""

from django.conf import settings
from django.db import models

from apps.content.models import Answer, Lesson, Question, Ticket


class LessonResult(models.Model):
    """One completed run of a lesson test."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="lesson_results")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="results")
    score = models.PositiveIntegerField()
    total = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["user", "lesson", "-score"])]

    def __str__(self) -> str:
        return f"{self.user_id} · {self.lesson_id} · {self.score}/{self.total}"

    @property
    def passed(self) -> bool:
        return self.total > 0 and self.score >= round(self.total * settings.LESSON_PASS_RATIO)


class TicketResult(models.Model):
    """One completed bilet."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="ticket_results")
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="results")
    score = models.PositiveIntegerField()
    total = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["user", "ticket", "-score"])]


class ExamAttempt(models.Model):
    """A generated 20/50-question exam run."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="exam_attempts")
    question_count = models.PositiveIntegerField()
    score = models.PositiveIntegerField(default=0)
    pass_score = models.PositiveIntegerField()
    duration_seconds = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)

    @property
    def passed(self) -> bool:
        return self.score >= self.pass_score


class QuestionAttempt(models.Model):
    """Every answer the user submits — the source of the Mistakes screen."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="question_attempts")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="attempts")
    answer = models.ForeignKey(Answer, on_delete=models.SET_NULL, null=True, blank=True)
    is_correct = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["user", "question", "-created_at"])]


class SavedQuestion(models.Model):
    """Foydalanuvchi saqlab qo'ygan savol (mobil "Saqlanganlar" ro'yxati)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="saved_questions")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="saved_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "question")
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["user", "-created_at"])]
        verbose_name = "Saqlangan savol"
        verbose_name_plural = "Saqlangan savollar"

    def __str__(self) -> str:
        return f"{self.user_id} · q{self.question_id}"


class Mistake(models.Model):
    """Aggregated wrong-answer counter per user+question.

    Kept denormalised so the Mistakes screen is a single indexed query
    instead of a GROUP BY over every attempt.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="mistakes")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="mistakes")
    wrong_count = models.PositiveIntegerField(default=0)
    last_wrong_answer = models.ForeignKey(
        Answer, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    resolved = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "question")
        ordering = ("-wrong_count", "-updated_at")
        indexes = [models.Index(fields=["user", "resolved", "-wrong_count"])]

    def __str__(self) -> str:
        return f"{self.user_id} · q{self.question_id} · {self.wrong_count}x"
