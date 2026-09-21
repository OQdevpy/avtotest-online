from django.db import models
import uuid

class Student(models.Model):
    name = models.CharField(max_length=255, blank=True)
    token = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Talaba"
        verbose_name_plural = "Talabalar"

    def __str__(self):
        return f"{self.name} - {self.token}"
