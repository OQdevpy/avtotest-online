"""Filial va to'lov boshqaruvi — faqat shef uchun."""

from drf_spectacular.utils import extend_schema
from rest_framework import viewsets

from common.permissions import IsAdminRole

from .models import Branch, PaymentReport, Student, StudentPayment
from .serializers import (
    BranchSerializer,
    ManageStudentSerializer,
    PaymentReportSerializer,
    StudentPaymentSerializer,
)


@extend_schema(tags=["manage"])
class ManageBranchViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminRole]
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer


@extend_schema(tags=["manage"])
class ManageStudentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminRole]
    queryset = Student.objects.select_related("branch", "user")
    serializer_class = ManageStudentSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        branch = self.request.query_params.get("branch")
        return qs.filter(branch_id=branch) if branch else qs


@extend_schema(tags=["manage"])
class ManageStudentPaymentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminRole]
    queryset = StudentPayment.objects.select_related("user")
    serializer_class = StudentPaymentSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        branch = self.request.query_params.get("branch")
        return qs.filter(user__branch_id=branch) if branch else qs


@extend_schema(tags=["manage"])
class ManagePaymentReportViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminRole]
    queryset = PaymentReport.objects.select_related("student_payment")
    serializer_class = PaymentReportSerializer
