from django.contrib import admin

from .models import (
    ExamAttempt, LessonResult, Mistake, QuestionAttempt, SavedQuestion, TicketResult,
)


@admin.register(LessonResult)
class LessonResultAdmin(admin.ModelAdmin):
    list_display = ("user", "lesson", "score", "total", "created_at")
    list_filter = ("lesson__section",)
    search_fields = ("user__phone",)
    list_select_related = ("user", "lesson")


@admin.register(TicketResult)
class TicketResultAdmin(admin.ModelAdmin):
    list_display = ("user", "ticket", "score", "total", "created_at")
    search_fields = ("user__phone",)
    list_select_related = ("user", "ticket")


@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = ("user", "question_count", "score", "pass_score", "created_at")
    list_filter = ("question_count",)
    search_fields = ("user__phone",)


@admin.register(QuestionAttempt)
class QuestionAttemptAdmin(admin.ModelAdmin):
    list_display = ("user", "question", "is_correct", "created_at")
    list_filter = ("is_correct",)
    search_fields = ("user__phone",)
    list_select_related = ("user", "question")


@admin.register(SavedQuestion)
class SavedQuestionAdmin(admin.ModelAdmin):
    list_display = ("user", "question", "created_at")
    search_fields = ("user__phone",)
    list_select_related = ("user", "question")


@admin.register(Mistake)
class MistakeAdmin(admin.ModelAdmin):
    list_display = ("user", "question", "wrong_count", "resolved", "updated_at")
    list_filter = ("resolved",)
    search_fields = ("user__phone",)
    list_select_related = ("user", "question")
