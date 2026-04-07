from django.db import models

from app_core.models import TimestampedModel
from .tenant import Tenant


class TenantAccessPolicy(TimestampedModel):
    tenant = models.OneToOneField(
        Tenant,
        on_delete=models.CASCADE,
        related_name="access_policy",
        verbose_name="Tenant"
    )
    allowed_ip_ranges = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Разрешённые IP/CIDR"
    )
    is_ip_whitelist_enabled = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Whitelist включён"
    )
    policy_notes = models.TextField(
        blank=True,
        verbose_name="Комментарий"
    )

    class Meta:
        verbose_name = "Tenant access policy"
        verbose_name_plural = "Tenant access policies"

    def __str__(self) -> str:
        return f"Access policy: {self.tenant.code}"