from django.urls import path

from . import views

urlpatterns = [
    path("version/", views.AppVersionView.as_view(), name="app-version"),
    path("login-options/", views.LoginOptionsView.as_view(), name="app-login-options"),
]
