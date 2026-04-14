from decimal import Decimal

from django.db import models

from app_core.models import UUIDTimestampedModel
from app_assets.models import AssetContext
from app_providers.models.provider import Provider


class ProviderTransferFeeType(models.TextChoices):
    NONE = "none", "Нет комиссии"
    FIXED = "fixed", "Фиксированная"
    PERCENT = "percent", "Процентная"


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

    deposit_confirmations = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Подтверждений для ввода",
        help_text="Сколько подтверждений сети нужно для зачисления депозита.",
    )
    withdraw_confirmations = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Подтверждений для вывода",
        help_text="Если провайдер отдаёт такое значение отдельно, храним его здесь.",
    )

    deposit_fee_type = models.CharField(
        max_length=16,
        choices=ProviderTransferFeeType.choices,
        default=ProviderTransferFeeType.NONE,
        verbose_name="Тип комиссии на ввод",
    )
    deposit_fee_fixed = models.DecimalField(
        max_digits=30,
        decimal_places=18,
        null=True,
        blank=True,
        verbose_name="Фикс. комиссия на ввод",
        help_text="Комиссия в единицах самого актива.",
    )
    deposit_fee_percent = models.DecimalField(
        max_digits=12,
        decimal_places=8,
        null=True,
        blank=True,
        verbose_name="Комиссия на ввод, %",
        help_text="Процентная комиссия в долях. 0.01 = 1%.",
    )
    deposit_fee_min_amount = models.DecimalField(
        max_digits=30,
        decimal_places=18,
        null=True,
        blank=True,
        verbose_name="Мин. комиссия на ввод",
        help_text="Минимальная комиссия на ввод в единицах актива.",
    )
    deposit_fee_max_amount = models.DecimalField(
        max_digits=30,
        decimal_places=18,
        null=True,
        blank=True,
        verbose_name="Макс. комиссия на ввод",
        help_text="Максимальная комиссия на ввод в единицах актива.",
    )

    withdraw_fee_type = models.CharField(
        max_length=16,
        choices=ProviderTransferFeeType.choices,
        default=ProviderTransferFeeType.NONE,
        verbose_name="Тип комиссии на вывод",
    )
    withdraw_fee_fixed = models.DecimalField(
        max_digits=30,
        decimal_places=18,
        null=True,
        blank=True,
        verbose_name="Фикс. комиссия на вывод",
        help_text="Комиссия в единицах самого актива.",
    )
    withdraw_fee_percent = models.DecimalField(
        max_digits=12,
        decimal_places=8,
        null=True,
        blank=True,
        verbose_name="Комиссия на вывод, %",
        help_text="Процентная комиссия в долях. 0.01 = 1%.",
    )
    withdraw_fee_min_amount = models.DecimalField(
        max_digits=30,
        decimal_places=18,
        null=True,
        blank=True,
        verbose_name="Мин. комиссия на вывод",
        help_text="Минимальная комиссия на вывод в единицах актива.",
    )
    withdraw_fee_max_amount = models.DecimalField(
        max_digits=30,
        decimal_places=18,
        null=True,
        blank=True,
        verbose_name="Макс. комиссия на вывод",
        help_text="Максимальная комиссия на вывод в единицах актива.",
    )

    deposit_min_amount = models.DecimalField(
        max_digits=30,
        decimal_places=18,
        null=True,
        blank=True,
        verbose_name="Мин. сумма ввода",
        help_text="Минимальная сумма ввода в единицах актива.",
    )
    deposit_max_amount = models.DecimalField(
        max_digits=30,
        decimal_places=18,
        null=True,
        blank=True,
        verbose_name="Макс. сумма ввода",
        help_text="Максимальная сумма ввода в единицах актива, если провайдер её отдаёт.",
    )
    withdraw_min_amount = models.DecimalField(
        max_digits=30,
        decimal_places=18,
        null=True,
        blank=True,
        verbose_name="Мин. сумма вывода",
        help_text="Минимальная сумма вывода в единицах актива.",
    )
    withdraw_max_amount = models.DecimalField(
        max_digits=30,
        decimal_places=18,
        null=True,
        blank=True,
        verbose_name="Макс. сумма вывода",
        help_text="Максимальная сумма вывода в единицах актива, если провайдер её отдаёт.",
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
