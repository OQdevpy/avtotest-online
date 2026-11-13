from django.urls import path

from . import click, payme, views

urlpatterns = [
    path("payme/", payme.PaymeWebhookView.as_view(), name="payments-payme"),
    path("click/prepare/", click.ClickPrepareView.as_view(), name="payments-click-prepare"),
    path("click/complete/", click.ClickCompleteView.as_view(), name="payments-click-complete"),
    path("plans/", views.PlansView.as_view(), name="payments-plans"),
    path("checkout/", views.CheckoutView.as_view(), name="payments-checkout"),
    path("orders/<int:pk>/", views.OrderDetailView.as_view(), name="payments-order"),
    path("done/", views.DoneView.as_view(), name="payments-done"),
]
