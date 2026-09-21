from django.urls import path, include
from rest_framework.routers import DefaultRouter
from content.views import SectionViewSet, LessonViewSet, QuestionViewSet, RandomQuestionView, TicketViewSet
from students.views import LoginView

router = DefaultRouter()
router.register(r'sections', SectionViewSet, basename='section')
router.register(r'lessons', LessonViewSet, basename='lesson')
router.register(r'questions', QuestionViewSet, basename='question')
router.register(r'tickets', TicketViewSet, basename='ticket')

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('random-questions/', RandomQuestionView.as_view(), name='random-questions'),
    path('random-test/', RandomQuestionView.as_view(), name='random-test'),
    path('', include(router.urls)),
]
