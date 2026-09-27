from django.conf import settings
from django.db import transaction
from rest_framework import serializers

from apps.content.models import Answer, Blits, Lesson, Question, Ticket
from apps.content.serializers import QuestionSerializer
from .models import (
    BlitsResult,
    ExamAttempt, LessonResult, Mistake, QuestionAttempt, SavedQuestion, TicketResult,
)


class AttemptItemSerializer(serializers.Serializer):
    """One answered question inside a submitted run."""

    question = serializers.PrimaryKeyRelatedField(queryset=Question.objects.all())
    answer = serializers.PrimaryKeyRelatedField(
        queryset=Answer.objects.all(), allow_null=True, required=False
    )


def record_attempts(user, items) -> int:
    """Persist per-question attempts, update mistake counters, return score."""
    score = 0
    for item in items:
        question = item["question"]
        answer = item.get("answer")
        is_correct = bool(answer and answer.is_true and answer.question_id == question.id)
        if is_correct:
            score += 1

        QuestionAttempt.objects.create(
            user=user, question=question, answer=answer, is_correct=is_correct
        )

        mistake, _ = Mistake.objects.get_or_create(user=user, question=question)
        if is_correct:
            mistake.resolved = True
        else:
            mistake.wrong_count += 1
            mistake.last_wrong_answer = answer
            mistake.resolved = False
        mistake.save()
    return score


class LessonSubmitSerializer(serializers.Serializer):
    """POST body for finishing a lesson test."""

    lesson = serializers.PrimaryKeyRelatedField(queryset=Lesson.objects.all())
    items = AttemptItemSerializer(many=True)

    @transaction.atomic
    def create(self, validated):
        user = self.context["request"].user
        items = validated["items"]
        score = record_attempts(user, items)
        return LessonResult.objects.create(
            user=user, lesson=validated["lesson"], score=score, total=len(items)
        )


class LessonResultSerializer(serializers.ModelSerializer):
    passed = serializers.BooleanField(read_only=True)

    class Meta:
        model = LessonResult
        fields = ("id", "lesson", "score", "total", "passed", "created_at")


class TicketSubmitSerializer(serializers.Serializer):
    ticket = serializers.PrimaryKeyRelatedField(queryset=Ticket.objects.all())
    items = AttemptItemSerializer(many=True)

    @transaction.atomic
    def create(self, validated):
        user = self.context["request"].user
        items = validated["items"]
        score = record_attempts(user, items)
        return TicketResult.objects.create(
            user=user, ticket=validated["ticket"], score=score, total=len(items)
        )


class TicketResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketResult
        fields = ("id", "ticket", "score", "total", "created_at")


class BlitsSubmitSerializer(serializers.Serializer):
    blits = serializers.PrimaryKeyRelatedField(queryset=Blits.objects.all())
    items = AttemptItemSerializer(many=True)

    @transaction.atomic
    def create(self, validated):
        user = self.context["request"].user
        items = validated["items"]
        score = record_attempts(user, items)
        return BlitsResult.objects.create(
            user=user, blits=validated["blits"], score=score, total=len(items)
        )


class BlitsResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlitsResult
        fields = ("id", "blits", "score", "total", "created_at")


class ExamSubmitSerializer(serializers.Serializer):
    items = AttemptItemSerializer(many=True)
    duration_seconds = serializers.IntegerField(min_value=0, default=0)

    @transaction.atomic
    def create(self, validated):
        user = self.context["request"].user
        items = validated["items"]
        count = len(items)
        mode = settings.EXAM_MODES.get(count) or settings.EXAM_MODES[20]
        score = record_attempts(user, items)
        return ExamAttempt.objects.create(
            user=user,
            question_count=count,
            score=score,
            pass_score=mode["pass_score"],
            duration_seconds=validated["duration_seconds"],
        )


class ExamAttemptSerializer(serializers.ModelSerializer):
    passed = serializers.BooleanField(read_only=True)

    class Meta:
        model = ExamAttempt
        fields = (
            "id", "question_count", "score", "pass_score", "passed",
            "duration_seconds", "created_at",
        )


class MistakeSerializer(serializers.ModelSerializer):
    question = QuestionSerializer(read_only=True)

    class Meta:
        model = Mistake
        fields = ("id", "question", "wrong_count", "last_wrong_answer", "resolved", "updated_at")


class SavedQuestionSerializer(serializers.ModelSerializer):
    """Saqlangan savol ro'yxati uchun — savol to'liq, kaliti bilan."""

    question = QuestionSerializer(read_only=True)

    class Meta:
        model = SavedQuestion
        fields = ("id", "question", "created_at")


class SavedQuestionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedQuestion
        fields = ("question",)

    def create(self, validated):
        saved, _ = SavedQuestion.objects.get_or_create(
            user=self.context["request"].user, question=validated["question"]
        )
        return saved
