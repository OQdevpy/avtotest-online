from django.conf import settings
from rest_framework import serializers

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field

from common.compat import CompatFieldsMixin
from common.lang import TranslatedField
from .models import Answer, Blits, Lesson, Question, Section, Ticket, Topic


class AnswerSerializer(CompatFieldsMixin, serializers.ModelSerializer):
    text = TranslatedField("text")

    # Eski frontlar (web, darslik) uchun ?compat=1 da qo'shiladigan nomlar.
    compat_aliases = {
        "answer_uz": "text_uz",
        "answer_ru": "text_ru",
        "answer_cry": "text_cry",
        "tartib": "order",
    }

    class Meta:
        model = Answer
        fields = ("id", "text", "is_true", "order")


class AnswerPublicSerializer(AnswerSerializer):
    """Same as AnswerSerializer but hides which option is correct.

    Used while an exam is in progress so the client cannot read the key.
    """

    class Meta(AnswerSerializer.Meta):
        fields = ("id", "text", "order")


class QuestionSerializer(CompatFieldsMixin, serializers.ModelSerializer):
    text = TranslatedField("text")
    explanation = TranslatedField("explanation")
    image_url = serializers.SerializerMethodField()
    explanation_image_url = serializers.SerializerMethodField()
    audio_url = serializers.SerializerMethodField()
    answers = AnswerSerializer(many=True, read_only=True)

    compat_aliases = {
        "question_uz": "text_uz",
        "question_ru": "text_ru",
        "question_cry": "text_cry",
        "tartib": "order",
    }

    class Meta:
        model = Question
        fields = (
            "id", "lesson_id", "text", "explanation", "image", "image_url",
            "explanation_image", "explanation_image_url", "audio", "audio_url",
            "answers", "order",
        )

    def _media_url(self, path: str) -> str | None:
        if not path:
            return None
        request = self.context.get("request")
        url = f"{settings.MEDIA_URL}{path}"
        return request.build_absolute_uri(url) if request else url

    def get_image_url(self, obj) -> str | None:
        return self._media_url(obj.image)

    def get_explanation_image_url(self, obj) -> str | None:
        return self._media_url(obj.explanation_image)

    def get_audio_url(self, obj) -> str | None:
        return self._media_url(obj.audio)


class QuestionPublicSerializer(QuestionSerializer):
    answers = AnswerPublicSerializer(many=True, read_only=True)

    class Meta(QuestionSerializer.Meta):
        fields = ("id", "lesson_id", "text", "image", "image_url", "answers", "order")


class LessonSerializer(serializers.ModelSerializer):
    name = TranslatedField("name")
    question_count = serializers.IntegerField(read_only=True)
    # progress fields are annotated by the view for authenticated users
    best_score = serializers.IntegerField(read_only=True, default=0)
    is_done = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = ("id", "section_id", "name", "order", "question_count", "best_score", "is_done")

    def get_is_done(self, obj) -> bool:
        total = getattr(obj, "question_count", 0) or 0
        best = getattr(obj, "best_score", 0) or 0
        return total > 0 and best >= round(total * settings.LESSON_PASS_RATIO)


class LessonDetailSerializer(LessonSerializer):
    questions = serializers.SerializerMethodField()

    class Meta(LessonSerializer.Meta):
        fields = LessonSerializer.Meta.fields + ("questions",)

    @extend_schema_field(QuestionSerializer(many=True))
    def get_questions(self, obj):
        # `hide_answers` bo'lsa to'g'ri javob chiqmaydi. Ilgari bu yerda
        # QuestionSerializer shartsiz ishlatilardi va javob kaliti test
        # rejimida ham oshkor bo'lardi.
        serializer_cls = (
            QuestionPublicSerializer
            if self.context.get("hide_answers")
            else QuestionSerializer
        )
        return serializer_cls(obj.questions.all(), many=True, context=self.context).data


class SectionSerializer(serializers.ModelSerializer):
    name = TranslatedField("name")
    lesson_count = serializers.IntegerField(read_only=True, default=0)
    done_count = serializers.IntegerField(read_only=True, default=0)
    # Rang bo'yicha darslar soni (prefetch qilingan `lessons`dan hisoblanadi):
    #   green  — eng yaxshi natija >= LESSON_GREEN_RATIO (90%)
    #   red    — ishlangan, lekin 90% dan past
    #   (yellow = lesson_count - green - red — ishlanmagan, mijozда hisoblanadi)
    green_count = serializers.SerializerMethodField()
    red_count = serializers.SerializerMethodField()

    class Meta:
        model = Section
        fields = (
            "id", "name", "order", "lesson_count", "done_count",
            "green_count", "red_count",
        )

    @staticmethod
    def _lesson_color(lesson) -> str:
        total = getattr(lesson, "question_count", 0) or 0
        best = getattr(lesson, "best_score", None)
        if best is None:
            return "yellow"  # ishlanmagan
        if total > 0 and best >= total * settings.LESSON_GREEN_RATIO:
            return "green"
        return "red"

    def _colors(self, obj):
        # `lessons` prefetch qilinmagan bo'lsa (0,0) — N+1 so'rovдан saqlanamiz.
        cache = getattr(obj, "_prefetched_objects_cache", None)
        if not cache or "lessons" not in cache:
            return 0, 0
        green = red = 0
        for ls in obj.lessons.all():
            c = self._lesson_color(ls)
            if c == "green":
                green += 1
            elif c == "red":
                red += 1
        return green, red

    def get_green_count(self, obj) -> int:
        return self._colors(obj)[0]

    def get_red_count(self, obj) -> int:
        return self._colors(obj)[1]


class SectionDetailSerializer(SectionSerializer):
    lessons = LessonSerializer(many=True, read_only=True)

    class Meta(SectionSerializer.Meta):
        fields = SectionSerializer.Meta.fields + ("lessons",)


class TopicSerializer(serializers.ModelSerializer):
    name = TranslatedField("name")
    question_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Topic
        fields = ("id", "name", "order", "question_count")


class TopicDetailSerializer(TopicSerializer):
    """Mavzu + uning savollari (mobil `TopicDetail` ekrani)."""

    questions = serializers.SerializerMethodField()

    class Meta(TopicSerializer.Meta):
        fields = TopicSerializer.Meta.fields + ("questions",)

    @extend_schema_field(QuestionSerializer(many=True))
    def get_questions(self, obj):
        qs = self._visible(obj.questions).prefetch_related("answers")
        serializer_cls = (
            QuestionPublicSerializer
            if self.context.get("hide_answers")
            else QuestionSerializer
        )
        return serializer_cls(qs, many=True, context=self.context).data

    def _visible(self, related):
        """Nashr etilmaganini kesib tashlaydi (o'qituvchi/shefga hammasi ochiq)."""
        allowed = self.context.get("visible_questions")
        if allowed is None:
            return related
        return related.filter(pk__in=allowed.values("pk"))


class TicketSerializer(serializers.ModelSerializer):
    question_count = serializers.IntegerField(read_only=True, default=0)
    best_score = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Ticket
        fields = ("id", "number", "question_count", "best_score", "is_pro")


class TicketDetailSerializer(TicketSerializer):
    questions = serializers.SerializerMethodField()

    class Meta(TicketSerializer.Meta):
        fields = TicketSerializer.Meta.fields + ("questions",)

    @extend_schema_field(QuestionSerializer(many=True))
    def get_questions(self, obj):
        items = obj.items.select_related("question").prefetch_related("question__answers")
        allowed = self.context.get("visible_questions")
        if allowed is not None:
            visible_ids = set(allowed.values_list("pk", flat=True))
            items = [item for item in items if item.question_id in visible_ids]
        qs = [item.question for item in items]
        serializer_cls = (
            QuestionPublicSerializer
            if self.context.get("hide_answers")
            else QuestionSerializer
        )
        return serializer_cls(qs, many=True, context=self.context).data


class BlitsSerializer(serializers.ModelSerializer):
    name = TranslatedField("name")
    question_count = serializers.SerializerMethodField()

    class Meta:
        model = Blits
        fields = ("id", "name", "order", "question_count")

    @extend_schema_field(OpenApiTypes.INT)
    def get_question_count(self, obj) -> int:
        allowed = self.context.get("visible_questions")
        items = obj.items
        if allowed is not None:
            items = items.filter(question__in=allowed.values("pk"))
        return items.count()


class BlitsDetailSerializer(BlitsSerializer):
    questions = serializers.SerializerMethodField()

    class Meta(BlitsSerializer.Meta):
        fields = BlitsSerializer.Meta.fields + ("questions",)

    @extend_schema_field(QuestionSerializer(many=True))
    def get_questions(self, obj):
        items = obj.items.select_related("question").prefetch_related("question__answers")
        allowed = self.context.get("visible_questions")
        if allowed is not None:
            visible_ids = set(allowed.values_list("pk", flat=True))
            items = [item for item in items if item.question_id in visible_ids]
        serializer_cls = (
            QuestionPublicSerializer
            if self.context.get("hide_answers")
            else QuestionSerializer
        )
        return serializer_cls([i.question for i in items], many=True,
                              context=self.context).data
