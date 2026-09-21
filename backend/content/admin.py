from django.contrib import admin
from .models import Section, Lesson, Question, Answer, Ticket, TicketQuestion

class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 1

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('name_uz', 'order', 'created_at')
    search_fields = ('name_uz', 'name_ru', 'name_cry')
    list_editable = ('order',)

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('name_uz', 'section', 'order', 'created_at')
    list_filter = ('section',)
    search_fields = ('name_uz', 'name_ru', 'name_cry')
    list_editable = ('order',)
    autocomplete_fields = ('section',)

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'short_text', 'lesson', 'order')
    list_filter = ('lesson__section', 'lesson')
    search_fields = ('text_uz', 'text_ru', 'text_cry')
    inlines = [AnswerInline]
    autocomplete_fields = ('lesson',)
    
    def short_text(self, obj):
        return obj.text_uz[:60] + ("..." if len(obj.text_uz) > 60 else "")
    short_text.short_description = "Savol"

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('short_text', 'question', 'is_true', 'order')
    list_filter = ('is_true',)
    search_fields = ('text_uz', 'text_ru', 'text_cry')
    autocomplete_fields = ('question',)

    def short_text(self, obj):
        return obj.text_uz[:50] + ("..." if len(obj.text_uz) > 50 else "")
    short_text.short_description = "Javob"

class TicketQuestionInline(admin.TabularInline):
    model = TicketQuestion
    extra = 1
    autocomplete_fields = ('question',)

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('number', 'is_pro')
    list_filter = ('is_pro',)
    search_fields = ('number',)
    inlines = [TicketQuestionInline]
