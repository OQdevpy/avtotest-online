"""Imtihon endpointlari.

`start/` sessiyani ochadi va savollarni beradi; `answer/` javoblarni yig'adi;
`finish/` serverda baholaydi. Mijoz yuborgan ballga ishonilmaydi.
"""

import random
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.http import Http404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.content.views import question_serializer_for, visible_questions
from apps.progress.serializers import ExamAttemptSerializer
from common.lang import resolve_lang

from .grading import grade_session
from .models import ExamSession, ExamSessionQuestion
from .serializers import (
    ExamAnswerSerializer,
    ExamResultSerializer,
    ExamSessionSerializer,
    ExamStartSerializer,
)


def owned_session(request, pk: int) -> ExamSession:
    session = ExamSession.objects.filter(pk=pk, user=request.user).first()
    if session is None:
        raise Http404
    return session


@extend_schema(tags=["exams"], request=ExamStartSerializer)
class ExamStartView(APIView):
    """Yangi imtihon sessiyasi. Savollar serverda tanlanadi va yozib qo'yiladi."""

    @transaction.atomic
    def post(self, request):
        serializer = ExamStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mode_key = serializer.validated_data["mode"]
        mode = settings.EXAM_MODES[mode_key]

        pool = list(visible_questions(request).values_list("id", flat=True))
        if len(pool) < mode["questions"]:
            return Response(
                {"detail": f"Savollar yetarli emas: {len(pool)} ta bor, "
                           f"{mode['questions']} ta kerak."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        picked = random.sample(pool, mode["questions"])
        session = ExamSession.objects.create(
            user=request.user,
            mode=mode_key,
            ends_at=timezone.now() + timedelta(minutes=mode["minutes"]),
            pass_score=mode["pass_score"],
        )
        ExamSessionQuestion.objects.bulk_create(
            ExamSessionQuestion(session=session, question_id=qid, order=index)
            for index, qid in enumerate(picked)
        )

        questions = (
            visible_questions(request)
            .filter(id__in=picked)
            .prefetch_related("answers")
        )
        # Savollar tanlangan tartibda qaytadi (queryset tartibi boshqa).
        by_id = {q.id: q for q in questions}
        ordered = [by_id[qid] for qid in picked if qid in by_id]

        context = {"request": request, "lang": resolve_lang(request)}
        payload = question_serializer_for(request)(
            ordered, many=True, context=context
        ).data
        return Response({
            **ExamSessionSerializer(session).data,
            "minutes": mode["minutes"],
            "questions": payload,
        })


@extend_schema(tags=["exams"], request=ExamAnswerSerializer)
class ExamAnswerView(APIView):
    """Bitta javobni saqlaydi. Vaqt tugagach 409."""

    def post(self, request, pk: int):
        session = owned_session(request, pk)
        if not session.is_open:
            return Response(
                {"detail": "Imtihon vaqti tugagan yoki yakunlangan."},
                status=status.HTTP_409_CONFLICT,
            )

        serializer = ExamAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        item = session.items.filter(question_id=data["question"]).first()
        if item is None:
            return Response({"question": "Bu savol shu imtihonda yo'q."},
                            status=status.HTTP_400_BAD_REQUEST)

        answer_id = data.get("answer")
        if answer_id is not None and not item.question.answers.filter(
            pk=answer_id
        ).exists():
            return Response({"answer": "Javob bu savolga tegishli emas."},
                            status=status.HTTP_400_BAD_REQUEST)

        item.answer_id = answer_id
        item.save(update_fields=["answer"])
        return Response({"question": item.question_id, "answer": answer_id})


@extend_schema(tags=["exams"], request=None)
class ExamFinishView(APIView):
    """Imtihonni yakunlaydi va serverda baholaydi. Ikkinchi chaqiruvda 409."""

    def post(self, request, pk: int):
        session = owned_session(request, pk)
        if session.finished_at is not None:
            return Response({"detail": "Imtihon allaqachon yakunlangan."},
                            status=status.HTTP_409_CONFLICT)
        grade_session(session)
        session.refresh_from_db()
        return Response(ExamResultSerializer(session).data)


@extend_schema(tags=["exams"])
class ExamSessionDetailView(generics.RetrieveAPIView):
    serializer_class = ExamResultSerializer

    def get_queryset(self):
        return ExamSession.objects.filter(user=self.request.user).prefetch_related("items")


@extend_schema(tags=["exams"])
class ExamSessionListView(generics.ListAPIView):
    serializer_class = ExamSessionSerializer

    def get_queryset(self):
        return ExamSession.objects.filter(user=self.request.user)
