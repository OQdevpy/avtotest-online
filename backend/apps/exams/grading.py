"""Imtihonni baholash — faqat serverda.

`grade_session` idempotent: sessiya allaqachon yakunlangan bo'lsa mavjud
`ExamAttempt` qaytadi va ball qayta hisoblanmaydi. Shuning uchun `finish/`
ikki marta chaqirilsa ikkinchi natija yozuvi paydo bo'lmaydi.
"""

from django.db import transaction
from django.utils import timezone

from apps.progress.models import ExamAttempt, Mistake, QuestionAttempt


@transaction.atomic
def grade_session(session):
    """Sessiyani baholaydi va `ExamAttempt` qaytaradi."""
    session = (
        type(session).objects.select_for_update().get(pk=session.pk)
    )
    if session.attempt_id is not None:
        return session.attempt

    items = list(session.items.select_related("answer", "question"))
    score = 0
    for item in items:
        answer = item.answer
        is_correct = bool(
            answer and answer.is_true and answer.question_id == item.question_id
        )
        item.is_correct = is_correct
        if is_correct:
            score += 1

        QuestionAttempt.objects.create(
            user_id=session.user_id, question_id=item.question_id,
            answer=answer, is_correct=is_correct,
        )
        mistake, _ = Mistake.objects.get_or_create(
            user_id=session.user_id, question_id=item.question_id
        )
        if is_correct:
            mistake.resolved = True
        else:
            mistake.wrong_count += 1
            mistake.last_wrong_answer = answer
            mistake.resolved = False
        mistake.save()

    session.items.model.objects.bulk_update(items, ["is_correct"])

    now = timezone.now()
    attempt = ExamAttempt.objects.create(
        user_id=session.user_id,
        question_count=len(items),
        score=score,
        pass_score=session.pass_score,
        duration_seconds=int((now - session.started_at).total_seconds()),
    )
    session.score = score
    session.finished_at = now
    session.attempt = attempt
    session.save(update_fields=["score", "finished_at", "attempt"])
    return attempt
