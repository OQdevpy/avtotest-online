import random

from django.conf import settings
from django.db.models import Count, OuterRef, Prefetch, Subquery
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.progress.models import LessonResult, TicketResult
from common.lang import LangSerializerContextMixin, resolve_lang
from .models import Lesson, Question, Section, Ticket, Topic
from .serializers import (
    LessonDetailSerializer,
    LessonSerializer,
    QuestionPublicSerializer,
    QuestionSerializer,
    SectionDetailSerializer,
    SectionSerializer,
    TicketDetailSerializer,
    TicketSerializer,
    TopicDetailSerializer,
    TopicSerializer,
)

LANG_PARAM = OpenApiParameter(
    name="lang",
    description="Kontent tili: uz | kr | qq | ru (standart: uz)",
    required=False,
    type=str,
)


def annotate_lesson_progress(qs, user):
    """Attach `question_count` and the user's `best_score` to a Lesson queryset."""
    qs = qs.annotate(question_count=Count("questions", distinct=True))
    if user and user.is_authenticated:
        best = (
            LessonResult.objects
            .filter(user=user, lesson=OuterRef("pk"))
            .order_by("-score")
            .values("score")[:1]
        )
        qs = qs.annotate(best_score=Subquery(best))
    return qs


# --- Sections ---------------------------------------------------------------

@extend_schema(tags=["content"], parameters=[LANG_PARAM])
class SectionListView(LangSerializerContextMixin, generics.ListAPIView):
    """Bo'limlar ro'yxati (mobil `Lessons` ekrani)."""

    serializer_class = SectionSerializer
    pagination_class = None

    def get_queryset(self):
        # Darslarni foydalanuvchi natijalari bilan prefetch qilamiz —
        # serializer har bo'lim uchun yashil/qizil darslar sonini hisoblaydi.
        lessons = annotate_lesson_progress(Lesson.objects.all(), self.request.user)
        return (
            Section.objects
            .annotate(lesson_count=Count("lessons", distinct=True))
            .prefetch_related(Prefetch("lessons", queryset=lessons))
        )


@extend_schema(tags=["content"], parameters=[LANG_PARAM])
class SectionDetailView(LangSerializerContextMixin, generics.RetrieveAPIView):
    """Bitta bo'lim va uning darslari (mobil `LessonSection` ekrani)."""

    serializer_class = SectionDetailSerializer

    def get_queryset(self):
        lessons = annotate_lesson_progress(Lesson.objects.all(), self.request.user)
        return (
            Section.objects
            .annotate(lesson_count=Count("lessons", distinct=True))
            .prefetch_related(Prefetch("lessons", queryset=lessons))
        )


# --- Lessons ----------------------------------------------------------------

@extend_schema(
    tags=["content"],
    parameters=[
        LANG_PARAM,
        OpenApiParameter("section", description="Bo'lim id bo'yicha filtr", required=False, type=int),
    ],
)
class LessonListView(LangSerializerContextMixin, generics.ListAPIView):
    serializer_class = LessonSerializer
    pagination_class = None

    def get_queryset(self):
        qs = annotate_lesson_progress(Lesson.objects.all(), self.request.user)
        section = self.request.query_params.get("section")
        return qs.filter(section_id=section) if section else qs


@extend_schema(tags=["content"], parameters=[LANG_PARAM])
class LessonDetailView(LangSerializerContextMixin, generics.RetrieveAPIView):
    """Dars savollari va javoblari bilan (mobil `LessonDetail` ekrani)."""

    serializer_class = LessonDetailSerializer

    def get_queryset(self):
        questions = Question.objects.prefetch_related("answers")
        return annotate_lesson_progress(
            Lesson.objects.prefetch_related(Prefetch("questions", queryset=questions)),
            self.request.user,
        )


# --- Topics -----------------------------------------------------------------

@extend_schema(tags=["content"], parameters=[LANG_PARAM])
class TopicListView(LangSerializerContextMixin, generics.ListAPIView):
    """Mavzular ro'yxati (mobil `Topics` ekrani)."""

    serializer_class = TopicSerializer
    pagination_class = None
    queryset = Topic.objects.annotate(question_count=Count("questions", distinct=True))


@extend_schema(
    tags=["content"],
    parameters=[
        LANG_PARAM,
        OpenApiParameter(
            "mode",
            description="`study` bo'lsa to'g'ri javob ochiq qaytadi, aks holda yashiriladi",
            required=False,
            type=str,
        ),
    ],
)
class TopicDetailView(LangSerializerContextMixin, generics.RetrieveAPIView):
    """Bitta mavzu va uning savollari (mobil `TopicDetail` ekrani)."""

    serializer_class = TopicDetailSerializer
    queryset = Topic.objects.annotate(question_count=Count("questions", distinct=True))

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["hide_answers"] = self.request.query_params.get("mode") != "study"
        return ctx


# --- Tickets ----------------------------------------------------------------

class TicketQuerysetMixin:
    def get_queryset(self):
        qs = Ticket.objects.annotate(question_count=Count("items", distinct=True))
        user = self.request.user
        if user.is_authenticated:
            best = (
                TicketResult.objects
                .filter(user=user, ticket=OuterRef("pk"))
                .order_by("-score")
                .values("score")[:1]
            )
            qs = qs.annotate(best_score=Subquery(best))
        return qs


@extend_schema(tags=["content"], parameters=[LANG_PARAM])
class TicketListView(TicketQuerysetMixin, LangSerializerContextMixin, generics.ListAPIView):
    """Biletlar ro'yxati (mobil `Biletlar` ekrani)."""

    serializer_class = TicketSerializer


@extend_schema(
    tags=["content"],
    parameters=[
        LANG_PARAM,
        OpenApiParameter(
            "mode",
            description="`study` bo'lsa to'g'ri javob ochiq qaytadi, aks holda yashiriladi",
            required=False,
            type=str,
        ),
    ],
)
class TicketDetailView(TicketQuerysetMixin, LangSerializerContextMixin, generics.RetrieveAPIView):
    serializer_class = TicketDetailSerializer
    lookup_field = "number"

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        # Hide the answer key unless the client explicitly asks to study.
        ctx["hide_answers"] = self.request.query_params.get("mode") != "study"
        return ctx

    def get_object(self):
        ticket = super().get_object()
        # PRO bilet — obunasiz foydalanuvchiga savollar berilmaydi.
        if ticket.is_pro and not self.request.user.pro_active:
            raise PermissionDenied("Bu bilet faqat PRO obuna uchun.")
        return ticket


@extend_schema(tags=["content"], description="Biletlar bo'yicha umumiy statistika kartalari.")
class TicketStatsView(APIView):
    def get(self, request):
        total = Ticket.objects.count()
        done = 0
        avg = 0.0
        if request.user.is_authenticated:
            results = TicketResult.objects.filter(user=request.user)
            done = results.values("ticket").distinct().count()
            scores = list(results.values_list("score", "total"))
            if scores:
                avg = round(
                    100 * sum(s for s, _ in scores) / max(sum(t for _, t in scores), 1), 1
                )
        return Response({"total": total, "done": done, "avg_percent": avg})


# --- Exam -------------------------------------------------------------------

@extend_schema(
    tags=["exam"],
    parameters=[
        LANG_PARAM,
        OpenApiParameter("count", description="20 yoki 50", required=False, type=int),
        OpenApiParameter(
            "mode",
            description="`study` bo'lsa to'g'ri javob ochiq qaytadi (mobil test rejimi "
            "javobni belgilash bilanoq ko'rsatadi), aks holda yashiriladi",
            required=False,
            type=str,
        ),
    ],
    description="Tasodifiy imtihon savollarini generatsiya qiladi (mobil `Exam` ekrani).",
)
class ExamGenerateView(APIView):
    def get(self, request):
        try:
            count = int(request.query_params.get("count", 20))
        except ValueError:
            count = 20
        mode = settings.EXAM_MODES.get(count, settings.EXAM_MODES[20])

        ids = list(Question.objects.values_list("id", flat=True))
        picked = random.sample(ids, min(mode["questions"], len(ids)))
        questions = Question.objects.filter(id__in=picked).prefetch_related("answers")

        context = {"request": request, "lang": resolve_lang(request)}
        # `study` rejimida to'g'ri javob ochiq keladi — mijoz javob belgilangan
        # zahoti yashil/qizilni ko'rsatadi.
        serializer_class = (
            QuestionSerializer
            if request.query_params.get("mode") == "study"
            else QuestionPublicSerializer
        )
        data = serializer_class(questions, many=True, context=context).data
        return Response(
            {
                "count": len(data),
                "minutes": mode["minutes"],
                "pass_score": mode["pass_score"],
                "questions": data,
            }
        )
