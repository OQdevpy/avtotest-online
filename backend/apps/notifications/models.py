"""Notifications backing the mobile Profile badge + Notifications screen.

A notification is either broadcast (user=None, visible to everyone) or
targeted at one user. Read state lives in a separate table so a broadcast
row is stored once no matter how many users read it.
"""

from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Kind(models.TextChoices):
        EXAM = "exam", "Imtihon"
        LESSON = "lesson", "Dars"
        PRO = "pro", "PRO obuna"
        OCTAGON = "octagon", "Octagon"
        INFO = "info", "Ma'lumot"

    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.INFO)
    title_uz = models.CharField(max_length=255)
    title_ru = models.CharField(max_length=255, blank=True)
    title_cry = models.CharField(max_length=255, blank=True)
    body_uz = models.TextField(blank=True)
    body_ru = models.TextField(blank=True)
    body_cry = models.TextField(blank=True)

    # None => broadcast to every user
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["user", "is_active", "-created_at"])]
        verbose_name = "Bildirishnoma"
        verbose_name_plural = "Bildirishnomalar"

    def __str__(self) -> str:
        return self.title_uz

    @property
    def is_broadcast(self) -> bool:
        return self.user_id is None


class NotificationRead(models.Model):
    notification = models.ForeignKey(
        Notification, on_delete=models.CASCADE, related_name="reads"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_reads"
    )
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("notification", "user")
        indexes = [models.Index(fields=["user", "notification"])]

    def __str__(self) -> str:
        return f"{self.user_id} read {self.notification_id}"
