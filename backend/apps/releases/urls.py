from django.urls import path

from . import views

urlpatterns = [
    path("version/", views.AppVersionView.as_view(), name="app-version"),
]
