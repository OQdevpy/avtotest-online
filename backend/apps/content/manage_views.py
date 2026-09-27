"""Shef (admin) uchun kontent CRUD.

Barchasi `IsAdminRole` bilan yopilgan. O'quvchi va o'qituvchi bu yo'llarga
kira olmaydi — kontent nazorati faqat shefda.
"""

from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.permissions import IsAdminRole

from .manage_serializers import (
    ManageAnswerSerializer,
    ManageBlitsSerializer,
    ManageLessonSerializer,
    ManageQuestionSerializer,
    ManageSectionSerializer,
    ManageTicketSerializer,
    ManageTopicSerializer,
    ReorderSerializer,
)
from .models import Answer, Blits, Lesson, Question, Section, Ticket, Topic


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
class ManageQuestionViewSet(ReorderMixin, viewsets.ModelViewSet):
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
class ManageTopicViewSet(ReorderMixin, viewsets.ModelViewSet):
    permission_classes = [IsAdminRole]
    queryset = Topic.objects.all()
    serializer_class = ManageTopicSerializer


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
