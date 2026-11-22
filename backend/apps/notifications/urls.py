from django.urls import path

from . import views

urlpatterns = [
    path("", views.NotificationListView.as_view(), name="notification-list"),
    path("unread-count/", views.UnreadCountView.as_view(), name="notification-unread-count"),
    path("read-all/", views.MarkAllReadView.as_view(), name="notification-read-all"),
    path("devices/", views.PushDeviceRegisterView.as_view(), name="push-device-register"),
    path("devices/remove/", views.PushDeviceRemoveView.as_view(), name="push-device-remove"),
    path("<int:pk>/read/", views.MarkReadView.as_view(), name="notification-read"),
]
