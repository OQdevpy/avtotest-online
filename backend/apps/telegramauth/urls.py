from django.urls import path

from . import views

# Bu URL'lar config/urls.py'da `auth/` ostiga ulanadi:
#   POST /api/v1/auth/send-code/
#   POST /api/v1/auth/verify-code/
#   POST /api/v1/auth/reset-password/
urlpatterns = [
    path("send-code/", views.SendCodeView.as_view(), name="send-code"),
    path("verify-code/", views.VerifyCodeView.as_view(), name="verify-code"),
    path("telegram/start/", views.TelegramStartView.as_view(), name="telegram-start"),
    path("telegram/status/<str:token>/", views.TelegramStatusView.as_view(),
         name="telegram-status"),
    path("telegram/return/", views.AppReturnView.as_view(), name="telegram-app-return"),
    path("reset-password/", views.ResetPasswordView.as_view(), name="reset-password"),
]
