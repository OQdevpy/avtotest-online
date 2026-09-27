from django.contrib import admin

from .models import Branch, PaymentReport, StudentPayment


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at")
    search_fields = ("name",)


class PaymentReportInline(admin.TabularInline):
    model = PaymentReport
    extra = 0


@admin.register(StudentPayment)
class StudentPaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "amount", "tolagani", "qoldiq", "created_at")
    search_fields = ("user__phone", "user__full_name")
    list_filter = ("user__branch",)
    inlines = [PaymentReportInline]


@admin.register(PaymentReport)
class PaymentReportAdmin(admin.ModelAdmin):
    list_display = ("id", "student_payment", "paid_amount", "date")
    list_filter = ("date",)
