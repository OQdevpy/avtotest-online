"""Shef uchun `manage/` marshrutlari — kontent qismi."""

from rest_framework.routers import DefaultRouter

from . import manage_views

router = DefaultRouter()
router.register(r"sections", manage_views.ManageSectionViewSet, basename="manage-section")
router.register(r"lessons", manage_views.ManageLessonViewSet, basename="manage-lesson")
router.register(r"questions", manage_views.ManageQuestionViewSet, basename="manage-question")
router.register(r"answers", manage_views.ManageAnswerViewSet, basename="manage-answer")
router.register(r"tickets", manage_views.ManageTicketViewSet, basename="manage-ticket")
router.register(r"blits", manage_views.ManageBlitsViewSet, basename="manage-blits")
router.register(r"blits-questions", manage_views.ManageBlitsQuestionViewSet,
                basename="manage-blits-question")

urlpatterns = router.urls
