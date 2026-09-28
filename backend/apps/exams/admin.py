from django.contrib import admin

from .models import ExamSession, ExamSessionQuestion


class ExamSessionQuestionInline(admin.TabularInline):
    model = ExamSessionQuestion
    extra = 0
    readonly_fields = ("question", "order", "answer", "is_correct")
    can_delete = False


@admin.register(ExamSession)
class ExamSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "mode", "score", "pass_score", "started_at", "finished_at")
    list_filter = ("mode", "finished_at")
    search_fields = ("user__phone", "user__full_name")
    inlines = [ExamSessionQuestionInline]
