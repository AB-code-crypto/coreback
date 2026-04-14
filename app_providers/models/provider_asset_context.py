from django.db import models

from app_core.models import UUIDTimestampedModel
from app_assets.models import AssetContext
from app_providers.models.provider import Provider


class ProviderAssetContext(UUIDTimestampedModel):
    provider = models.ForeignKey(
        Provider,
        on_delete=models.CASCADE,
        related_name="asset_contexts",
        verbose_name="Провайдер",
    )
    asset_context = models.ForeignKey(
        AssetContext,
        on_delete=models.CASCADE,
        related_name="provider_links",
        verbose_name="AssetContext",
    )

    provider_code = models.CharField(
        max_length=128,
        db_index=True,
        verbose_name="Код у провайдера",
        help_text="Как эта сущность называется у конкретного провайдера.",
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Активен",
        help_text="Используется ли эта связка в системе.",
    )

    deposit_enabled = models.BooleanField(
        default=False,
        verbose_name="Ввод средств",
        help_text="Можно ли принимать этот инструмент у провайдера.",
    )
    withdraw_enabled = models.BooleanField(
        default=False,
        verbose_name="Вывод средств",
        help_text="Можно ли выводить этот инструмент через провайдера.",
    )

    description = models.TextField(
        blank=True,
        verbose_name="Описание",
    )

    class Meta:
        verbose_name = "AssetContext провайдера"
        verbose_name_plural = "04 AssetContext провайдеров"
        ordering = ("provider", "provider_code")
        indexes = [
            models.Index(fields=["provider", "is_active"]),
            models.Index(fields=["provider", "provider_code"]),
            models.Index(fields=["asset_context", "is_active"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_code"],
                name="uniq_provider_asset_context_code",
            ),
            models.UniqueConstraint(
                fields=["provider", "asset_context"],
                name="uniq_provider_asset_context_pair",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.provider.code} | {self.provider_code}"

    def save(self, *args, **kwargs):
        if self.provider_code:
            self.provider_code = self.provider_code.strip()

        if self.description:
            self.description = self.description.strip()

        super().save(*args, **kwargs)
