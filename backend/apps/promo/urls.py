from django.urls import path

from . import views

urlpatterns = [
    path("", views.SlideListView.as_view(), name="slide-list"),
]
