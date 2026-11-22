from rest_framework import serializers

from .models import Slide


class SlideSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Slide
        fields = ("id", "image_url", "action", "url")

    def get_image_url(self, obj) -> str:
        url = obj.image_for(self.context["lang"]).url
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request else url
