from django.contrib import admin

from .models import (
    Answer,
    Blits,
    BlitsQuestion,
    Lesson,
    Question,
    Section,
    Ticket,
    TicketQuestion,
    Topic,
)


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0
    fields = ("name_uz", "name_ru", "name_cry", "order")


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("order", "name_uz", "name_ru", "lesson_count")
    ordering = ("order",)
    search_fields = ("name_uz", "name_ru", "name_cry")
    inlines = [LessonInline]

    @admin.display(description="Darslar")
    def lesson_count(self, obj):
        return obj.lessons.count()


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("order", "name_uz", "section", "question_count")
    list_filter = ("section",)
    search_fields = ("name_uz", "name_ru", "name_cry")

    @admin.display(description="Savollar")
    def question_count(self, obj):
        return obj.questions.count()


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0
    fields = ("text_uz", "text_ru", "text_cry", "is_true", "order")


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "short_text", "lesson", "is_published", "is_in_web",
                    "has_image", "answer_count")
    list_filter = ("is_published", "is_in_web", "lesson__section", "lesson")
    search_fields = ("text_uz", "text_ru", "text_cry")
    list_editable = ("is_published",)
    inlines = [AnswerInline]
    list_select_related = ("lesson",)
    actions = ("publish", "unpublish")

    @admin.action(description="Nashr etish (o'quvchiga ko'rinadi)")
    def publish(self, request, queryset):
        count = queryset.update(is_published=True)
        self.message_user(request, f"{count} ta savol nashr etildi.")

    @admin.action(description="Nashrdan olish (o'quvchiga ko'rinmaydi)")
    def unpublish(self, request, queryset):
        count = queryset.update(is_published=False)
        self.message_user(request, f"{count} ta savol nashrdan olindi.")

    @admin.display(description="Savol")
    def short_text(self, obj):
        return obj.text_uz[:70]

    @admin.display(boolean=True, description="Rasm")
    def has_image(self, obj):
        return bool(obj.image)

    @admin.display(description="Javoblar")
    def answer_count(self, obj):
        return obj.answers.count()


class TicketQuestionInline(admin.TabularInline):
    model = TicketQuestion
    extra = 0
    raw_id_fields = ("question",)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("number", "question_count", "is_pro")
    list_filter = ("is_pro",)
    list_editable = ("is_pro",)
    inlines = [TicketQuestionInline]

    @admin.display(description="Savollar")
    def question_count(self, obj):
        return obj.items.count()


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("order", "name_uz", "question_count")
    search_fields = ("name_uz", "name_ru", "name_cry")

    @admin.display(description="Savollar")
    def question_count(self, obj):
        return obj.questions.count()


class BlitsQuestionInline(admin.TabularInline):
    model = BlitsQuestion
    extra = 0
    autocomplete_fields = ("question",)


@admin.register(Blits)
class BlitsAdmin(admin.ModelAdmin):
    list_display = ("id", "name_uz", "order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name_uz", "name_ru", "name_cry")
    inlines = [BlitsQuestionInline]


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("id", "question", "text_uz", "is_true", "order")
    list_filter = ("is_true",)
    search_fields = ("text_uz", "text_ru", "text_cry")
    autocomplete_fields = ("question",)
