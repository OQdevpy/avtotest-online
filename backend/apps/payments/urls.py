from django.urls import path

from . import payme, views

urlpatterns = [
    path("payme/", payme.PaymeWebhookView.as_view(), name="payments-payme"),
    path("plans/", views.PlansView.as_view(), name="payments-plans"),
    path("checkout/", views.CheckoutView.as_view(), name="payments-checkout"),
    path("orders/<int:pk>/", views.OrderDetailView.as_view(), name="payments-order"),
    path("done/", views.DoneView.as_view(), name="payments-done"),
]
