from rest_framework import serializers

from common.lang import TranslatedField
from .models import Notification, PushDevice


class NotificationSerializer(serializers.ModelSerializer):
    title = TranslatedField("title")
    body = TranslatedField("body")
    # annotated by the view
    is_read = serializers.BooleanField(read_only=True, default=False)

    class Meta:
        model = Notification
        fields = ("id", "kind", "title", "body", "is_read", "created_at")


class UnreadCountSerializer(serializers.Serializer):
    unread = serializers.IntegerField()


class PushDeviceSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=255)
    platform = serializers.ChoiceField(choices=PushDevice.Platform.choices)
    app_version = serializers.CharField(max_length=32, required=False, allow_blank=True, default="")


class PushTokenSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=255)
