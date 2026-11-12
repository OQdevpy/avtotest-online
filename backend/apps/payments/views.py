"""Ilova uchun API: tariflar, to'lovni boshlash, buyurtma holati, qaytish sahifasi."""

from django.shortcuts import get_object_or_404, render
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from common.lang import resolve_lang

from . import links, services
from .models import PaymentConfig, ProOrder, ProPlan, Provider
from .serializers import (
    PLATFORMS,
    CheckoutResponseSerializer,
    CheckoutSerializer,
    PlansResponseSerializer,
    ProOrderSerializer,
    ProPlanSerializer,
)

DONE_PATH = "/api/v1/payments/done/"


def _error(code: str, detail: str, http_status=status.HTTP_400_BAD_REQUEST):
    return Response({"code": code, "detail": detail}, status=http_status)


@extend_schema(tags=["payments"])
class PlansView(APIView):
    @extend_schema(
        parameters=[OpenApiParameter("platform", str, enum=list(PLATFORMS)),
                    OpenApiParameter("lang", str)],
        responses=PlansResponseSerializer,
    )
    def get(self, request):
        platform = request.query_params.get("platform", "android")
        plans = ProPlan.objects.filter(is_active=True)
        context = {"lang": resolve_lang(request)}
        return Response({
            "plans": ProPlanSerializer(plans, many=True, context=context).data,
            "providers": services.available_providers(PaymentConfig.get(), platform),
        })


@extend_schema(tags=["payments"])
class CheckoutView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "payments_checkout"

    @extend_schema(request=CheckoutSerializer, responses={201: CheckoutResponseSerializer})
    def post(self, request):
        user = request.user
        if user.is_guest:
            return _error("register_required", "To'lov uchun ro'yxatdan o'ting.",
                          status.HTTP_403_FORBIDDEN)
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        plan = ProPlan.objects.filter(pk=data["plan"], is_active=True).first()
        if plan is None:
            return _error("plan_unavailable", "Tarif mavjud emas.")
        config = PaymentConfig.get()
        if data["provider"] not in services.available_providers(config, data["platform"]):
            return _error("provider_unavailable", "Bu to'lov usuli hozir mavjud emas.")
        if user.is_pro and user.pro_until is None:
            return _error("already_unlimited", "Sizda muddatsiz PRO bor.")

        order = ProOrder.objects.create(
            user=user, plan=plan, title=plan.title_uz, days=plan.days, amount=plan.price,
            provider=data["provider"],
        )
        return_url = request.build_absolute_uri(DONE_PATH)
        if order.provider == Provider.PAYME:
            url = links.payme_url(order, config, user.language, return_url)
        else:
            url = links.click_url(order, config, return_url)
        return Response({
            "order_id": order.id, "amount": order.amount, "days": order.days,
            "provider": order.provider, "payment_url": url,
        }, status=status.HTTP_201_CREATED)


@extend_schema(tags=["payments"], responses=ProOrderSerializer)
class OrderDetailView(APIView):
    def get(self, request, pk: int):
        order = get_object_or_404(ProOrder.objects.select_related("user"),
                                  pk=pk, user=request.user)
        return Response(ProOrderSerializer(order).data)


@extend_schema(exclude=True)
class DoneView(APIView):
    """Payme/Click to'lovdan keyin qaytaradigan sahifa. Hech qanday ma'lumot ko'rsatmaydi."""

    permission_classes = (AllowAny,)
    authentication_classes = ()

    def get(self, request):
        return render(request, "payments/done.html")
