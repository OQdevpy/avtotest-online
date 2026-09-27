from django.urls import path

from . import views

# Bu URL'lar config/urls.py'da `auth/` ostiga ulanadi:
#   POST /api/v1/auth/send-code/
#   POST /api/v1/auth/verify-code/
#   POST /api/v1/auth/reset-password/
urlpatterns = [
    path("send-code/", views.SendCodeView.as_view(), name="send-code"),
    path("verify-code/", views.VerifyCodeView.as_view(), name="verify-code"),
    path("reset-password/", views.ResetPasswordView.as_view(), name="reset-password"),
]
