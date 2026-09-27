from django.urls import path
from rest_framework_simplejwt.views import TokenVerifyView

from . import views

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("login-code/", views.AccessCodeLoginView.as_view(), name="login-code"),
    path("social/", views.SocialLoginView.as_view(), name="social-login"),
    path("token/refresh/", views.DeviceAwareTokenRefreshView.as_view(), name="token-refresh"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("devices/", views.DeviceListView.as_view(), name="device-list"),
    path("devices/<int:pk>/", views.DeviceDeleteView.as_view(), name="device-delete"),
    path("token/verify/", TokenVerifyView.as_view(), name="token-verify"),
    path("me/", views.MeView.as_view(), name="me"),
    path("change-password/", views.ChangePasswordView.as_view(), name="change-password"),
]
