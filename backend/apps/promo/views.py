from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics

from common.lang import resolve_lang

from .models import Slide
from .serializers import SlideSerializer


@extend_schema(
    tags=["promo"],
    parameters=[OpenApiParameter("lang", str, description="uz | kr | ru")],
    description="Bosh sahifa karuseli: faol slaydlar, foydalanuvchi tilidagi rasm bilan.",
)
class SlideListView(generics.ListAPIView):
    serializer_class = SlideSerializer
    pagination_class = None

    def get_queryset(self):
        return Slide.visible_to(self.request.user)

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "lang": resolve_lang(self.request)}
