from django.urls import path

from apps.accounts.views import UpdateRequiredView

from . import views

# Bu URL'lar config/urls.py'da `auth/` ostiga ulanadi. Kirish faqat Telegram
# orqali: telegram/start -> (bot) -> telegram/status -> telegram/claim.
# send-code, verify-code, reset-password — yopilgan (update_required).
urlpatterns = [
    path("send-code/", UpdateRequiredView.as_view(), name="send-code"),
    path("verify-code/", UpdateRequiredView.as_view(), name="verify-code"),
    path("telegram/start/", views.TelegramStartView.as_view(), name="telegram-start"),
    path("telegram/status/<str:token>/", views.TelegramStatusView.as_view(),
         name="telegram-status"),
    path("telegram/claim/", views.TelegramClaimView.as_view(), name="telegram-claim"),
    path("telegram/return/", views.AppReturnView.as_view(), name="telegram-app-return"),
    path("reset-password/", UpdateRequiredView.as_view(), name="reset-password"),
]
