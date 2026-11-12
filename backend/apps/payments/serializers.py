from rest_framework import serializers

from common.lang import TranslatedField

from .models import ProOrder, ProPlan, Provider

PLATFORMS = ("ios", "android")


class ProPlanSerializer(serializers.ModelSerializer):
    title = TranslatedField("title")

    class Meta:
        model = ProPlan
        fields = ("id", "title", "days", "price")


class PlansResponseSerializer(serializers.Serializer):
    plans = ProPlanSerializer(many=True)
    providers = serializers.ListField(child=serializers.ChoiceField(Provider.choices))


class CheckoutSerializer(serializers.Serializer):
    plan = serializers.IntegerField()
    provider = serializers.ChoiceField(Provider.choices)
    platform = serializers.ChoiceField(PLATFORMS, default="android")


class CheckoutResponseSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    amount = serializers.IntegerField()
    days = serializers.IntegerField()
    provider = serializers.CharField()
    payment_url = serializers.URLField()


class ProOrderSerializer(serializers.ModelSerializer):
    pro_until = serializers.SerializerMethodField()
    pro_active = serializers.SerializerMethodField()

    class Meta:
        model = ProOrder
        fields = ("id", "status", "days", "amount", "provider", "paid_at",
                  "pro_until", "pro_active")

    def get_pro_until(self, obj) -> str | None:
        user = obj.user
        return serializers.DateTimeField().to_representation(user.pro_until) \
            if user and user.pro_until else None

    def get_pro_active(self, obj) -> bool:
        return bool(obj.user and obj.user.pro_active)
