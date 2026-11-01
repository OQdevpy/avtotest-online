from django.core.validators import MinLengthValidator
from rest_framework import serializers

from .models import Branch, PaymentReport, Student, StudentPayment


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ("id", "name", "created_at")


class ManageStudentSerializer(serializers.ModelSerializer):
    """Shef talaba yaratadi/tahrirlaydi — parol ochiq matnda kiritiladi.

    Saqlanganda `apps.billing.signals` bog'liq `User`ni avtomatik
    yaratadi/yangilaydi (student=foydalanuvchi qoidasi).
    """

    # Tahrirlashda bo'sh qoldirilsa PIN o'zgarmaydi (talaba parolni o'zi tiklagan
    # bo'lsa PIN bo'sh — u o'z paroli bilan kiradi).
    password = serializers.CharField(
        max_length=10, required=False, allow_blank=True,
        validators=[MinLengthValidator(6, "Parol kamida 6 xonadan iborat bo'lishi kerak.")],
    )

    class Meta:
        model = Student
        fields = ("id", "user", "name", "branch", "phone", "password", "hujjat",
                  "is_active", "is_online", "created_at", "updated_at")
        read_only_fields = ("user", "created_at", "updated_at")

    def validate(self, attrs):
        if not attrs.get("password"):
            attrs.pop("password", None)
            if self.instance is None:
                raise serializers.ValidationError({"password": "Parol kiritilishi shart."})
        return attrs


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
