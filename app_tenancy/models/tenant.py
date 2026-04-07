from django.db import models

from app_core.models import UUIDTimestampedModel


class Tenant(UUIDTimestampedModel):
    code = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        verbose_name="Код"
    )
    name = models.CharField(
        max_length=255,
        verbose_name="Название"
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Активен"
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Заметки"
    )

    class Meta:
        verbose_name = "Tenant"
        verbose_name_plural = "Tenants"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"
