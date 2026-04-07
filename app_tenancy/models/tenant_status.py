from django.db import models

from app_core.models import TimestampedModel
from .tenant import Tenant


class TenantStatus(TimestampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        BLOCKED = "blocked", "Blocked"
        GRACE = "grace", "Grace"

    tenant = models.OneToOneField(
        Tenant,
        on_delete=models.CASCADE,
        related_name="status_record",
        verbose_name="Tenant"
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
        verbose_name="Статус"
    )
    reason = models.TextField(
        blank=True,
        verbose_name="Причина"
    )

    class Meta:
        verbose_name = "Tenant status"
        verbose_name_plural = "Tenant statuses"

    def __str__(self) -> str:
        return f"{self.tenant.code}: {self.status}"