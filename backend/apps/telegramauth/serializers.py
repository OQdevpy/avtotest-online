from rest_framework import serializers

from .models import Purpose


class TelegramClaimSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=64)
    # Mehmonning refresh tokeni — yangi hisob o'rniga mehmon hisobi aylanadi.
    guest_refresh = serializers.CharField(required=False, allow_blank=True)
    platform = serializers.CharField(max_length=10, required=False, allow_blank=True)
    device_label = serializers.CharField(max_length=120, required=False, allow_blank=True)


class TelegramStartSerializer(serializers.Serializer):
    # Raqam so'ralmaydi — bot uni kontaktdan oladi.
    purpose = serializers.ChoiceField(choices=Purpose.choices, required=False,
                                      default=Purpose.AUTH)
    lang = serializers.CharField(max_length=3, required=False, default="uz")
