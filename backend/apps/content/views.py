import random

from django.conf import settings
from django.db.models import Count, OuterRef, Prefetch, Q, Subquery
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.progress.models import LessonResult, TicketResult
from common.lang import LangSerializerContextMixin, resolve_lang
from .models import Blits, Lesson, Question, Section, Ticket


def visible_questions(request):
    """Shu so'rov ko'rishi mumkin bo'lgan savollar.

    O'quvchi faqat nashr etilganini ko'radi; o'qituvchi va shef hammasini —
    ular kontentni tekshiradi.
    """
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated and user.is_teacher:
        return Question.objects.all()
    return Question.published.all()


def question_serializer_for(request):
    """To'g'ri javob ochiq keladigan serializer tanlanadimi.

    `?mode=study` so'ralgan yoki so'rovchi o'qituvchi/shef bo'lsa — ochiq.
    """
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated and user.is_teacher:
        return QuestionSerializer
    if request.query_params.get("mode") == "study":
        return QuestionSerializer
    return QuestionPublicSerializer


def hide_answers_for(request) -> bool:
    """Serializer kontekstidagi `hide_answers` qiymati."""
    return question_serializer_for(request) is QuestionPublicSerializer
from .serializers import (
    LessonDetailSerializer,
    LessonSerializer,
    BlitsDetailSerializer,
    BlitsSerializer,
    QuestionPublicSerializer,
    QuestionSerializer,
    SectionDetailSerializer,
    SectionSerializer,
    TicketDetailSerializer,
    TicketSerializer,
)

LANG_PARAM = OpenApiParameter(
    name="lang",
    description="Kontent tili: uz | kr | qq | ru (standart: uz)",
    required=False,
    type=str,
)


def int_param(request, name: str):
    """`?name=` ni butun son sifatida o'qiydi. Yaroqsiz qiymat → 400, 500 emas."""
    raw = request.query_params.get(name)
    if raw in (None, ""):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        raise ValidationError({name: "Butun son bo'lishi kerak."})


def published_only(request) -> bool:
    """So'rovchi faqat nashr etilgan savollarni ko'radimi."""
    user = getattr(request, "user", None)
    return not (user is not None and user.is_authenticated and user.is_teacher)


def count_questions(request, relation: str):
    """`question_count` uchun Count — nashr etilmaganini hisobga olmaydi.

    Mijoz progress chizig'ini va savol soniqni shu raqamdan chizadi, shuning
    uchun u ko'rinadigan savollar soniga teng bo'lishi shart.
    """
    if published_only(request):
        return Count(relation, distinct=True,
                     filter=Q(**{f"{relation}__is_published": True}))
    return Count(relation, distinct=True)


def annotate_lesson_progress(qs, user, request=None):
    """Attach `question_count` and the user's `best_score` to a Lesson queryset."""
    relation = "questions"
    if request is not None and published_only(request):
        qs = qs.annotate(question_count=Count(
            relation, distinct=True,
            filter=Q(questions__is_published=True),
        ))
    else:
        qs = qs.annotate(question_count=Count(relation, distinct=True))
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
        lessons = annotate_lesson_progress(Lesson.objects.all(), self.request.user,
                                           self.request)
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
        lessons = annotate_lesson_progress(Lesson.objects.all(), self.request.user,
                                           self.request)
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
        qs = annotate_lesson_progress(Lesson.objects.all(), self.request.user,
                                           self.request)
        section = int_param(self.request, "section")
        return qs.filter(section_id=section) if section else qs


@extend_schema(tags=["content"], parameters=[LANG_PARAM])
class LessonDetailView(LangSerializerContextMixin, generics.RetrieveAPIView):
    """Dars savollari va javoblari bilan (mobil `LessonDetail` ekrani)."""

    serializer_class = LessonDetailSerializer

    def get_queryset(self):
        questions = visible_questions(self.request).prefetch_related("answers")
        return annotate_lesson_progress(
            Lesson.objects.prefetch_related(Prefetch("questions", queryset=questions)),
            self.request.user,
            self.request,
        )

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        # Dars ekrani — O'RGANISH rejimi: to'g'ri javob, izoh va audio ataylab
        # ochiq keladi. Do'kondagi mobil ilova bu yo'lni `?mode=study` siz
        # chaqiradi va yashil javobni, karnayni, izohni shu maydonlardan
        # chizadi. Kalit yopiladigan joylar — bilet, blits va imtihon.
        ctx["hide_answers"] = False
        return ctx


# --- Topics -------------------------------------------------------------
# "Mavzular" (Topic) alohida jadval sifatida hech qachon to'ldirilmagan
# (import buyruqlarining birortasi uni yozmagan) — shef panelida u doim
# bo'sh ko'rinardi. Shef qarori: Mavzular = Darslar, bitta ma'lumot manbai.
# /topics/ yo'li mobil ilova bilan moslik uchun saqlanadi, lekin endi
# to'g'ridan-to'g'ri Lesson'dan uzatiladi.

class TopicListView(LessonListView):
    """Mavzular ro'yxati — Darslar bilan bir xil (mobil `Topics` ekrani)."""


class TopicDetailView(LessonDetailView):
    """Bitta mavzu va uning savollari — Darslar bilan bir xil."""


# --- Tickets ----------------------------------------------------------------

class TicketQuerysetMixin:
    def get_queryset(self):
        if published_only(self.request):
            counter = Count("items", distinct=True,
                            filter=Q(items__question__is_published=True))
        else:
            counter = Count("items", distinct=True)
        # `filter=` bilan annotate GROUP BY qo'shadi va Meta.ordering tushib
        # qoladi — sahifalash barqaror bo'lishi uchun tartib aniq beriladi.
        qs = Ticket.objects.annotate(question_count=counter).order_by("number")
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
        # To'g'ri javob faqat `?mode=study` da yoki o'qituvchi/shefga ochiq.
        ctx["hide_answers"] = hide_answers_for(self.request)
        ctx["visible_questions"] = visible_questions(self.request)
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
    deprecated=True,
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
    """DEPRECATED — `POST exams/start/` ni ishlating.

    Do'kondagi mobil ilova shu yo'ldan foydalanadi, shuning uchun ishlashda
    davom etadi. Server bu yerda sessiya yozmaydi va vaqtni nazorat qilmaydi.
    """

    def get(self, request):
        try:
            count = int(request.query_params.get("count", 20))
        except ValueError:
            count = 20
        mode = settings.EXAM_MODES.get(count, settings.EXAM_MODES[20])

        ids = list(visible_questions(request).values_list("id", flat=True))
        picked = random.sample(ids, min(mode["questions"], len(ids)))
        questions = visible_questions(request).filter(
            id__in=picked
        ).prefetch_related("answers")

        context = {"request": request, "lang": resolve_lang(request)}
        # `study` rejimida to'g'ri javob ochiq keladi — mijoz javob belgilangan
        # zahoti yashil/qizilni ko'rsatadi.
        serializer_class = question_serializer_for(request)
        data = serializer_class(questions, many=True, context=context).data
        return Response(
            {
                "count": len(data),
                "minutes": mode["minutes"],
                "pass_score": mode["pass_score"],
                "questions": data,
            }
        )


# --- Blits ------------------------------------------------------------------

class BlitsContextMixin:
    """Blits view'lari uchun umumiy kontekst: til, javob yashirish, ko'rinish."""

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["hide_answers"] = hide_answers_for(self.request)
        ctx["visible_questions"] = visible_questions(self.request)
        return ctx


@extend_schema(tags=["content"], parameters=[LANG_PARAM])
class BlitsListView(BlitsContextMixin, LangSerializerContextMixin, generics.ListAPIView):
    """Blits to'plamlari ro'yxati."""

    serializer_class = BlitsSerializer
    queryset = Blits.objects.filter(is_active=True)


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
class BlitsDetailView(BlitsContextMixin, LangSerializerContextMixin,
                      generics.RetrieveAPIView):
    """Bitta blits to'plami va uning savollari."""

    serializer_class = BlitsDetailSerializer
    queryset = Blits.objects.filter(is_active=True)


# --- Questions --------------------------------------------------------------

@extend_schema(
    tags=["content"],
    parameters=[
        LANG_PARAM,
        OpenApiParameter("lesson", description="Dars id'si bo'yicha filtr",
                         required=False, type=int),
        OpenApiParameter("section", description="Bo'lim id'si bo'yicha filtr",
                         required=False, type=int),
        OpenApiParameter("search", description="Savol matni bo'yicha qidiruv "
                                              "(uz, ru va kirill ustunlari)",
                         required=False, type=str),
        OpenApiParameter("mode", description="`study` bo'lsa to'g'ri javob ochiq keladi",
                         required=False, type=str),
    ],
)
class QuestionListView(LangSerializerContextMixin, generics.ListAPIView):
    """Savollar ro'yxati va qidiruv — admin-panel va darslik frontlari uchun."""

    def get_serializer_class(self):
        return question_serializer_for(self.request)

    def get_queryset(self):
        qs = visible_questions(self.request).prefetch_related("answers")
        params = self.request.query_params

        lesson = int_param(self.request, "lesson")
        if lesson:
            qs = qs.filter(lesson_id=lesson)

        section = int_param(self.request, "section")
        if section:
            qs = qs.filter(lesson__section_id=section)

        search = (params.get("search") or "").strip()
        if search:
            qs = qs.filter(
                Q(text_uz__icontains=search)
                | Q(text_ru__icontains=search)
                | Q(text_cry__icontains=search)
            )
        return qs
