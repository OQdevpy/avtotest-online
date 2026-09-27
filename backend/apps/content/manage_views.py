"""Shef (admin) uchun kontent CRUD.

Barchasi `IsAdminRole` bilan yopilgan. O'quvchi va o'qituvchi bu yo'llarga
kira olmaydi — kontent nazorati faqat shefda.
"""

from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from common.permissions import IsAdminRole

from .media import (
    UnreadableImage,
    UnsupportedAudio,
    remove_quietly,
    save_audio,
    to_webp,
    unique_name,
)
from .manage_serializers import (
    ManageAnswerSerializer,
    ManageBlitsQuestionSerializer,
    ManageBlitsSerializer,
    ManageLessonSerializer,
    ManageQuestionSerializer,
    ManageSectionSerializer,
    ManageTicketSerializer,
    ReorderSerializer,
)
from .models import Answer, Blits, BlitsQuestion, Lesson, Question, Section, Ticket


class ReorderMixin:
    """`POST .../reorder/` — `{"ids": [...]}` ro'yxatdagi o'rinni `order` ga yozadi."""

    @extend_schema(request=ReorderSerializer, responses={200: None})
    @action(detail=False, methods=["post"])
    def reorder(self, request):
        serializer = ReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = serializer.validated_data["ids"]

        model = self.queryset.model
        rows = {obj.pk: obj for obj in model.objects.filter(pk__in=ids)}
        missing = [pk for pk in ids if pk not in rows]
        if missing:
            # Hech narsa yozilmaydi — yarim tartiblangan holat qolmasin.
            return Response(
                {"ids": f"Topilmadi: {missing}"}, status=status.HTTP_400_BAD_REQUEST
            )

        for position, pk in enumerate(ids):
            rows[pk].order = position
        with transaction.atomic():
            model.objects.bulk_update(rows.values(), ["order"])
        return Response({"ids": ids})



# --- Rasm va audio yuklash --------------------------------------------------

class _MediaUploadMixin:
    """`manage/questions/{id}/image|audio/` — multipart yuklash."""

    def _uploaded(self, request):
        file = request.data.get("file")
        if not file:
            raise ValidationError({"file": "Fayl yuborilmadi."})
        return file

    @extend_schema(request=None, responses={200: None})
    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser])
    def image(self, request, pk=None):
        question = self.get_object()
        upload = self._uploaded(request)
        try:
            relative = to_webp(upload, unique_name(f"q{question.pk}"))
        except UnreadableImage as exc:
            raise ValidationError({"file": str(exc)}) from exc

        remove_quietly(question.image)
        question.image = relative
        question.save(update_fields=["image"])
        return Response({"image": relative})

    @extend_schema(request=None, responses={200: None})
    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser])
    def audio(self, request, pk=None):
        question = self.get_object()
        upload = self._uploaded(request)
        try:
            relative = save_audio(upload, unique_name(f"q{question.pk}"), upload.name)
        except UnsupportedAudio as exc:
            raise ValidationError({"file": str(exc)}) from exc

        remove_quietly(question.audio)
        question.audio = relative
        question.save(update_fields=["audio"])
        return Response({"audio": relative})

    # admin-panel'dagi "izoh rasmi" (description_image) shu maydonga to'g'ri
    # keladi. `image` bilan bir xil qoida: WebP'ga o'giriladi, eskisi o'chadi.
    @extend_schema(request=None, responses={200: None})
    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser],
            url_path="explanation-image")
    def explanation_image(self, request, pk=None):
        question = self.get_object()
        upload = self._uploaded(request)
        try:
            relative = to_webp(upload, unique_name(f"q{question.pk}_izoh"))
        except UnreadableImage as exc:
            raise ValidationError({"file": str(exc)}) from exc

        remove_quietly(question.explanation_image)
        question.explanation_image = relative
        question.save(update_fields=["explanation_image"])
        return Response({"explanation_image": relative})


@extend_schema(tags=["manage"])
class ManageSectionViewSet(ReorderMixin, viewsets.ModelViewSet):
    permission_classes = [IsAdminRole]
    queryset = Section.objects.all()
    serializer_class = ManageSectionSerializer


@extend_schema(tags=["manage"])
class ManageLessonViewSet(ReorderMixin, viewsets.ModelViewSet):
    permission_classes = [IsAdminRole]
    queryset = Lesson.objects.all()
    serializer_class = ManageLessonSerializer

    def get_queryset(self):
        section = self.request.query_params.get("section")
        qs = super().get_queryset()
        return qs.filter(section_id=section) if section else qs


@extend_schema(tags=["manage"])
class ManageQuestionViewSet(_MediaUploadMixin, ReorderMixin, viewsets.ModelViewSet):
    permission_classes = [IsAdminRole]
    # Shef nashr etilmaganini ham ko'radi — `Question.objects`, `published` emas.
    queryset = Question.objects.prefetch_related("answers")
    serializer_class = ManageQuestionSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        lesson = self.request.query_params.get("lesson")
        return qs.filter(lesson_id=lesson) if lesson else qs


@extend_schema(tags=["manage"])
class ManageAnswerViewSet(ReorderMixin, viewsets.ModelViewSet):
    permission_classes = [IsAdminRole]
    queryset = Answer.objects.all()
    serializer_class = ManageAnswerSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        question = self.request.query_params.get("question")
        return qs.filter(question_id=question) if question else qs


@extend_schema(tags=["manage"])
class ManageTicketViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminRole]
    queryset = Ticket.objects.prefetch_related("items")
    serializer_class = ManageTicketSerializer


@extend_schema(tags=["manage"])
class ManageBlitsViewSet(ReorderMixin, viewsets.ModelViewSet):
    permission_classes = [IsAdminRole]
    queryset = Blits.objects.prefetch_related("items")
    serializer_class = ManageBlitsSerializer


@extend_schema(tags=["manage"])
class ManageBlitsQuestionViewSet(ReorderMixin, viewsets.ModelViewSet):
    """Blits ichidagi savollarni qo'shish/o'chirish/tartiblash.

    `ManageBlitsSerializer.items` faqat o'qish uchun edi — shef qaysi savolni
    qaysi blitsga qo'shishni shu endpoint orqali yozadi:
    `POST manage/blits-questions/ {"blits": 1, "question": 55, "order": 0}`,
    `DELETE manage/blits-questions/{id}/` bog'lanishni (savolni o'zini emas)
    o'chiradi, `POST manage/blits-questions/reorder/ {"ids": [...]}` bitta
    blits ichidagi tartibni belgilaydi.
    """

    permission_classes = [IsAdminRole]
    queryset = BlitsQuestion.objects.select_related("question", "blits")
    serializer_class = ManageBlitsQuestionSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        blits = self.request.query_params.get("blits")
        return qs.filter(blits_id=blits) if blits else qs
