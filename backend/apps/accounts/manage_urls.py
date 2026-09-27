"""Shef (admin) uchun `manage/` marshrutlari — accounts qismi."""

from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"access-codes", views.ManageAccessCodeViewSet, basename="manage-access-code")

urlpatterns = router.urls
