"""Statistika hisoblash — bitta joyda.

`progress/stats/` (o'quvchi o'zi) va `teacher/students/{id}/stats/` (o'qituvchi
ko'radi) shu funksiyadan foydalanadi, shuning uchun bir xil raqam qaytadi.
"""

from django.db.models import Count, Q, Sum

from .models import (
    BlitsResult,
    ExamAttempt,
    LessonResult,
    Mistake,
    QuestionAttempt,
    TicketResult,
)


def user_stats(user) -> dict:
    """Statistika ekrani uchun umumiy raqamlar."""
    attempts = QuestionAttempt.objects.filter(user=user).aggregate(
        started=Count("id"),
        right=Count("id", filter=Q(is_correct=True)),
        wrong=Count("id", filter=Q(is_correct=False)),
    )
    lesson_results = LessonResult.objects.filter(user=user)
    exams = ExamAttempt.objects.filter(user=user)
    return {
        "questions": attempts,
        "lessons": {
            "runs": lesson_results.count(),
            "distinct": lesson_results.values("lesson").distinct().count(),
        },
        "tickets": {
            "done": TicketResult.objects.filter(user=user)
            .values("ticket").distinct().count(),
        },
        "blits": {
            "done": BlitsResult.objects.filter(user=user)
            .values("blits").distinct().count(),
        },
        "exams": {
            "attempts": exams.count(),
            "passed": sum(1 for attempt in exams if attempt.passed),
        },
        "mistakes": Mistake.objects.filter(
            user=user, resolved=False, wrong_count__gt=0
        ).count(),
    }
