from django.db.models import Count, Q, Sum
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.lang import LangSerializerContextMixin
from .models import (
    BlitsResult,
    ExamAttempt, LessonResult, Mistake, QuestionAttempt, SavedQuestion, TicketResult,
)
from .serializers import (
    BlitsResultSerializer,
    BlitsSubmitSerializer,
    ExamAttemptSerializer,
    ExamSubmitSerializer,
    LessonResultSerializer,
    LessonSubmitSerializer,
    MistakeSerializer,
    SavedQuestionCreateSerializer,
    SavedQuestionSerializer,
    TicketResultSerializer,
    TicketSubmitSerializer,
)


class OwnedListMixin:
    """Restricts a list to the requesting user."""

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)


# --- Lesson results ---------------------------------------------------------

@extend_schema(tags=["progress"])
class LessonResultListCreateView(OwnedListMixin, generics.ListCreateAPIView):
    """GET: dars natijalari tarixi. POST: yakunlangan dars testini yuborish."""

    queryset = LessonResult.objects.select_related("lesson")

    def get_serializer_class(self):
        return LessonSubmitSerializer if self.request.method == "POST" else LessonResultSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(LessonResultSerializer(result).data, status=status.HTTP_201_CREATED)


# --- Ticket results ---------------------------------------------------------

@extend_schema(tags=["progress"])
class TicketResultListCreateView(OwnedListMixin, generics.ListCreateAPIView):
    queryset = TicketResult.objects.select_related("ticket")

    def get_serializer_class(self):
        return TicketSubmitSerializer if self.request.method == "POST" else TicketResultSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(TicketResultSerializer(result).data, status=status.HTTP_201_CREATED)


# --- Exam attempts ----------------------------------------------------------

@extend_schema(tags=["progress"])
class ExamAttemptListCreateView(OwnedListMixin, generics.ListCreateAPIView):
    """POST — DEPRECATED, `POST exams/{id}/finish/` ni ishlating.

    Do'kondagi mobil ilova natijani shu yerga yuboradi. GET (statistika uchun)
    o'z kuchida qoladi.
    """

    queryset = ExamAttempt.objects.all()

    def get_serializer_class(self):
        return ExamSubmitSerializer if self.request.method == "POST" else ExamAttemptSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attempt = serializer.save()
        return Response(ExamAttemptSerializer(attempt).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["progress"], description="Blits natijasini yuborish va ro'yxat.")
class BlitsResultListCreateView(OwnedListMixin, generics.ListCreateAPIView):
    queryset = BlitsResult.objects.all()

    def get_serializer_class(self):
        return (
            BlitsSubmitSerializer if self.request.method == "POST"
            else BlitsResultSerializer
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(BlitsResultSerializer(result).data,
                        status=status.HTTP_201_CREATED)


# --- Mistakes ---------------------------------------------------------------

@extend_schema(tags=["progress"], description="Eng ko'p xato qilingan savollar (mobil `Mistakes`).")
class MistakeListView(LangSerializerContextMixin, OwnedListMixin, generics.ListAPIView):
    serializer_class = MistakeSerializer
    queryset = (
        Mistake.objects
        .filter(resolved=False, wrong_count__gt=0)
        .select_related("question")
        .prefetch_related("question__answers")
    )


@extend_schema(tags=["progress"], description="Bitta xatoni ro'yxatdan olib tashlash.")
class MistakeResolveView(APIView):
    def post(self, request, pk: int):
        updated = Mistake.objects.filter(user=request.user, pk=pk).update(resolved=True)
        if not updated:
            return Response({"detail": "Topilmadi."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"detail": "Xato hal qilindi deb belgilandi."})


# --- Saqlangan savollar -----------------------------------------------------

@extend_schema(tags=["progress"], description="Saqlangan savollar ro'yxati / savolni saqlash.")
class SavedQuestionListCreateView(LangSerializerContextMixin, OwnedListMixin,
                                  generics.ListCreateAPIView):
    """GET: saqlangan savollar. POST: `{question: id}` — takrorlansa xato bermaydi."""

    queryset = (
        SavedQuestion.objects
        .select_related("question")
        .prefetch_related("question__answers")
    )

    def get_serializer_class(self):
        return (
            SavedQuestionCreateSerializer
            if self.request.method == "POST"
            else SavedQuestionSerializer
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        saved = serializer.save()
        out = SavedQuestionSerializer(saved, context=self.get_serializer_context())
        return Response(out.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["progress"], description="Savolni saqlanganlardan olib tashlash.")
class SavedQuestionDeleteView(APIView):
    def delete(self, request, question_id: int):
        deleted, _ = SavedQuestion.objects.filter(
            user=request.user, question_id=question_id
        ).delete()
        if not deleted:
            return Response({"detail": "Topilmadi."}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Stats / reset ----------------------------------------------------------

@extend_schema(tags=["progress"], description="Statistika ekrani uchun umumiy raqamlar.")
class StatsView(APIView):
    def get(self, request):
        user = request.user
        attempts = QuestionAttempt.objects.filter(user=user).aggregate(
            started=Count("id"),
            right=Count("id", filter=Q(is_correct=True)),
            wrong=Count("id", filter=Q(is_correct=False)),
        )
        lessons = LessonResult.objects.filter(user=user).aggregate(
            runs=Count("id"), best=Sum("score")
        )
        exams = ExamAttempt.objects.filter(user=user)
        return Response(
            {
                "questions": attempts,
                "lessons": {
                    "runs": lessons["runs"] or 0,
                    "distinct": LessonResult.objects.filter(user=user)
                    .values("lesson").distinct().count(),
                },
                "tickets": {
                    "done": TicketResult.objects.filter(user=user)
                    .values("ticket").distinct().count(),
                },
                "exams": {
                    "attempts": exams.count(),
                    "passed": sum(1 for e in exams if e.passed),
                },
                "mistakes": Mistake.objects.filter(
                    user=user, resolved=False, wrong_count__gt=0
                ).count(),
            }
        )


@extend_schema(tags=["progress"], description="Barcha statistikani tozalash (mobil Profil ekrani).")
class ResetProgressView(APIView):
    def post(self, request):
        user = request.user
        deleted = {
            "lesson_results": LessonResult.objects.filter(user=user).delete()[0],
            "ticket_results": TicketResult.objects.filter(user=user).delete()[0],
            "blits_results": BlitsResult.objects.filter(user=user).delete()[0],
            "exam_attempts": ExamAttempt.objects.filter(user=user).delete()[0],
            "question_attempts": QuestionAttempt.objects.filter(user=user).delete()[0],
            "mistakes": Mistake.objects.filter(user=user).delete()[0],
        }
        return Response({"detail": "Statistika tozalandi.", "deleted": deleted})
