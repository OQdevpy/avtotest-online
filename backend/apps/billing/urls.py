"""Shef uchun `manage/` marshrutlari — billing qismi."""

from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"branches", views.ManageBranchViewSet, basename="manage-branch")
router.register(r"payments", views.ManageStudentPaymentViewSet, basename="manage-payment")
router.register(r"payment-reports", views.ManagePaymentReportViewSet,
                basename="manage-payment-report")

urlpatterns = router.urls
