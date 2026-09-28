"""Shef uchun foydalanuvchi boshqaruvi.

O'quvchi yaratish — kirish kodini berishdan oldingi qadam. Parol faqat
yozish uchun va `set_password` orqali saqlanadi; javobda hech qachon qaytmaydi.
"""

from drf_spectacular.utils import extend_schema
from rest_framework import serializers, viewsets
from django.db.models import Q

from common.permissions import IsAdminRole

from .models import User
from .serializers import PhoneField


class ManageUserSerializer(serializers.ModelSerializer):
    phone = PhoneField(max_length=20)
    password = serializers.CharField(write_only=True, min_length=4, required=False)

    class Meta:
        model = User
        fields = (
            "id", "phone", "full_name", "role", "branch", "hujjat", "language",
            "is_active", "is_pro", "pro_until", "max_devices", "password", "date_joined",
        )
        read_only_fields = ("id", "date_joined")

    def create(self, validated):
        password = validated.pop("password", None)
        user = User(**validated)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated):
        password = validated.pop("password", None)
        user = super().update(instance, validated)
        if password:
            user.set_password(password)
            user.save(update_fields=["password"])
        return user


@extend_schema(tags=["manage"])
class ManageUserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminRole]
    queryset = User.objects.select_related("branch")
    serializer_class = ManageUserSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        role = params.get("role")
        if role:
            qs = qs.filter(role=role)

        branch = params.get("branch")
        if branch:
            qs = qs.filter(branch_id=branch)

        search = (params.get("search") or "").strip()
        if search:
            qs = qs.filter(Q(full_name__icontains=search) | Q(phone__icontains=search))
        return qs
