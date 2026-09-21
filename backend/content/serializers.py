from rest_framework import serializers
from .models import Section, Lesson, Question, Answer, Ticket

class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = '__all__'

class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = '__all__'

class AnswerSerializer(serializers.ModelSerializer):
    answer_uz = serializers.CharField(source='text_uz', read_only=True)
    answer_ru = serializers.CharField(source='text_ru', read_only=True)
    answer_cry = serializers.CharField(source='text_cry', read_only=True)

    class Meta:
        model = Answer
        fields = '__all__'

class QuestionSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True, read_only=True)
    lesson_name = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    question_uz = serializers.CharField(source='text_uz', read_only=True)
    question_ru = serializers.CharField(source='text_ru', read_only=True)
    question_cry = serializers.CharField(source='text_cry', read_only=True)

    class Meta:
        model = Question
        fields = '__all__'

    def get_lesson_name(self, obj):
        if obj.lesson:
            return {
                'name_uz': f"{obj.lesson.section.order}.{obj.lesson.name_uz}",
                'name_ru': f"{obj.lesson.section.order}.{obj.lesson.name_ru}",
                'name_cry': f"{obj.lesson.section.order}.{obj.lesson.name_cry}",
            }
        return {}

    def get_image(self, obj):
        if obj.image:
            import os
            base = os.path.basename(obj.image)
            name, ext = os.path.splitext(base)
            return name + '.webp'
        return ''

class TicketSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    class Meta:
        model = Ticket
        fields = '__all__'
