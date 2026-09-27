from rest_framework import serializers

from .models import Branch, PaymentReport, StudentPayment


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ("id", "name", "created_at")


class StudentPaymentSerializer(serializers.ModelSerializer):
    qoldiq = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = StudentPayment
        fields = ("id", "user", "amount", "tolagani", "qoldiq", "created_at")
        read_only_fields = ("tolagani",)


class PaymentReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentReport
        fields = ("id", "student_payment", "paid_amount", "date", "comment", "created_at")
