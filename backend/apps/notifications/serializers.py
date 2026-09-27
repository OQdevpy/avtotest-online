from rest_framework import serializers

from common.lang import TranslatedField
from .models import Notification


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
