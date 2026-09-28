"""Shef (admin) uchun `manage/` marshrutlari — accounts qismi."""

from rest_framework.routers import DefaultRouter

from . import manage_views, views

router = DefaultRouter()
router.register(r"users", manage_views.ManageUserViewSet, basename="manage-user")
router.register(r"access-codes", views.ManageAccessCodeViewSet, basename="manage-access-code")

urlpatterns = router.urls
