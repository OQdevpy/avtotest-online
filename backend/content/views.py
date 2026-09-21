from rest_framework import viewsets, views, status
from rest_framework.response import Response
from .models import Section, Lesson, Question, Ticket
from .serializers import SectionSerializer, LessonSerializer, QuestionSerializer, TicketSerializer
from students.permissions import HasValidTokenParam

class SectionViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [HasValidTokenParam]
    queryset = Section.objects.all()
    serializer_class = SectionSerializer

class LessonViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [HasValidTokenParam]
    serializer_class = LessonSerializer

    def get_queryset(self):
        qs = Lesson.objects.all()
        section = self.request.query_params.get('section')
        if section:
            qs = qs.filter(section_id=section)
        return qs

class QuestionViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [HasValidTokenParam]
    serializer_class = QuestionSerializer

    def get_queryset(self):
        qs = Question.objects.all()
        lesson = self.request.query_params.get('lesson')
        if lesson:
            qs = qs.filter(lesson_id=lesson)
        return qs

class RandomQuestionView(views.APIView):
    permission_classes = [HasValidTokenParam]
    def get(self, request):
        count = int(request.query_params.get('count', 20))
        section = request.query_params.get('section')
        qs = Question.objects.all()
        if section:
            qs = qs.filter(lesson__section_id=section)
        qs = qs.order_by('?')[:count]
        serializer = QuestionSerializer(qs, many=True)
        return Response(serializer.data)

class TicketViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [HasValidTokenParam]
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer
    lookup_field = 'number'
