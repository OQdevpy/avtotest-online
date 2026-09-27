"""Shef uchun kontent serializerlari.

Bu yerda til **yig'ilmaydi** — shef uchala ustunni (`*_uz`, `*_ru`, `*_cry`)
o'zi tahrirlaydi, shuning uchun hammasi ochiq keladi va yoziladi.
`common.lang.TranslatedField` ataylab ishlatilmaydi.
"""

from rest_framework import serializers

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


class ManageSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = "__all__"


class ManageLessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = "__all__"


class ManageAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = "__all__"


class ManageQuestionSerializer(serializers.ModelSerializer):
    answers = ManageAnswerSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = "__all__"


class ManageTopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = "__all__"


class ManageTicketQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketQuestion
        fields = ("id", "question", "order")


class ManageTicketSerializer(serializers.ModelSerializer):
    items = ManageTicketQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Ticket
        fields = ("id", "number", "is_pro", "items")


class ManageBlitsQuestionSerializer(serializers.ModelSerializer):
    """Blits ichidagi savol bog'lanishi.

    `blits` maydoni yozish uchun ochiq — admin-panel bitta so'rov bilan qaysi
    blitsga qaysi savol tegishli ekanini bildiradi (`manage/blits-questions/`).
    """

    class Meta:
        model = BlitsQuestion
        fields = ("id", "blits", "question", "order")


class ManageBlitsSerializer(serializers.ModelSerializer):
    items = ManageBlitsQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Blits
        fields = ("id", "name_uz", "name_ru", "name_cry", "order", "is_active", "items")


class ReorderSerializer(serializers.Serializer):
    """Drag-and-drop tartibi — ro'yxatdagi o'rin `order` ga aylanadi."""

    ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
