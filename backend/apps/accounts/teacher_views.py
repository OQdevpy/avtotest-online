"""O'qituvchi uchun o'quvchilar natijasi.

O'qituvchi faqat o'z filialidagi o'quvchilarni ko'radi; shef hammasini va
`?branch=` bilan filtrlaydi. Filialdan tashqaridagi id uchun 404 qaytadi —
403 emas, chunki hisobning mavjudligini ham oshkor qilmaslik kerak.
"""

from django.db.models import Count, Q
from drf_spectacular.utils import extend_schema
from rest_framework import generics, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.content.views import int_param
from apps.progress.services import user_stats
from common.permissions import IsTeacherOrAdmin

from .models import User


class StudentRowSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", default="", read_only=True)

    class Meta:
        model = User
        fields = ("id", "phone", "full_name", "branch", "branch_name",
                  "hujjat", "is_active", "date_joined")


def visible_students(request):
    """So'rovchi ko'rishi mumkin bo'lgan o'quvchilar."""
    qs = User.objects.filter(role=User.Role.STUDENT).select_related("branch")
    user = request.user
    if user.role == User.Role.TEACHER:
        # Filiali biriktirilmagan o'qituvchi hech kimni ko'rmaydi.
        if user.branch_id is None:
            return qs.none()
        return qs.filter(branch_id=user.branch_id)

    branch = int_param(request, "branch")
    return qs.filter(branch_id=branch) if branch else qs


@extend_schema(tags=["teacher"])
class TeacherStudentListView(generics.ListAPIView):
    permission_classes = [IsTeacherOrAdmin]
    serializer_class = StudentRowSerializer

    def get_queryset(self):
        return visible_students(self.request)


@extend_schema(tags=["teacher"])
class TeacherStudentStatsView(APIView):
    """Bitta o'quvchining natijalari va xatolari."""

    permission_classes = [IsTeacherOrAdmin]

    def get(self, request, pk: int):
        student = generics.get_object_or_404(visible_students(request), pk=pk)
        return Response({
            "student": StudentRowSerializer(student).data,
            "stats": user_stats(student),
        })


@extend_schema(tags=["teacher"])
class TeacherStatsView(APIView):
    """Filial kesimida umumiy ko'rsatkichlar."""

    permission_classes = [IsTeacherOrAdmin]

    def get(self, request):
        students = visible_students(request)
        by_branch = (
            students.values("branch", "branch__name")
            .annotate(
                student_count=Count("id"),
                with_document=Count("id", filter=Q(hujjat="+")),
            )
            .order_by("branch__name")
        )
        return Response({
            "student_count": students.count(),
            "branches": list(by_branch),
        })
