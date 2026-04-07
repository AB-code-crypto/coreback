from django.core.exceptions import ValidationError
from django.db import models

from app_core.models import TimestampedModel
from .provider import Provider


class ProviderOperationalStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    DEGRADED = "degraded", "Degraded"
    MAINTENANCE = "maintenance", "Maintenance"
    DISABLED = "disabled", "Disabled"
    ERROR = "error", "Error"


class ProviderStatus(TimestampedModel):
    provider = models.OneToOneField(
        Provider,
        on_delete=models.CASCADE,
        related_name="status",
        verbose_name="Провайдер",
    )
    status = models.CharField(
        max_length=32,
        choices=ProviderOperationalStatus.choices,
        default=ProviderOperationalStatus.ACTIVE,
        db_index=True,
        verbose_name="Общий статус",
        help_text=(
            "Агрегированное текущее состояние провайдера. "
            "Используется как общий operational-статус."
        ),
    )
    price_feed_enabled = models.BooleanField(
        default=True,
        verbose_name="Трансляция цен доступна",
        help_text="Можно ли сейчас получать цены от провайдера.",
    )
    deposit_enabled = models.BooleanField(
        default=False,
        verbose_name="Ввод средств доступен",
        help_text="Можно ли сейчас принимать средства через этого провайдера.",
    )
    address_generation_enabled = models.BooleanField(
        default=False,
        verbose_name="Генерация адресов доступна",
        help_text="Можно ли сейчас получать адреса для пополнения через этого провайдера.",
    )
    withdraw_enabled = models.BooleanField(
        default=False,
        verbose_name="Вывод средств доступен",
        help_text="Можно ли сейчас отправлять средства через этого провайдера.",
    )
    trade_execution_enabled = models.BooleanField(
        default=False,
        verbose_name="Исполнение сделок доступно",
        help_text="Можно ли сейчас выполнять обмены или торговые операции через этого провайдера.",
    )
    spot_trading_enabled = models.BooleanField(
        default=False,
        verbose_name="Спот доступен",
        help_text="Можно ли сейчас использовать спотовую торговлю через этого провайдера.",
    )
    futures_trading_enabled = models.BooleanField(
        default=False,
        verbose_name="Фьючерсы доступны",
        help_text="Можно ли сейчас использовать торговлю фьючерсами через этого провайдера.",
    )
    last_success_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Последний успешный доступ",
        help_text="Когда в последний раз взаимодействие с провайдером прошло успешно.",
    )
    last_error_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Последняя ошибка",
        help_text="Когда в последний раз была зафиксирована ошибка при работе с провайдером.",
    )
    last_error_message = models.TextField(
        blank=True,
        verbose_name="Текст последней ошибки",
        help_text="Последняя зафиксированная ошибка или причина деградации.",
    )

    class Meta:
        verbose_name = "Состояние"
        verbose_name_plural = "Состояние"

    def __str__(self) -> str:
        return self.provider.code

    def clean(self):
        errors = {}

        if self.address_generation_enabled and not self.deposit_enabled:
            errors["address_generation_enabled"] = (
                "Генерация адресов не может быть доступна, если ввод средств недоступен."
            )

        if self.spot_trading_enabled and not self.trade_execution_enabled:
            errors["spot_trading_enabled"] = (
                "Спотовая торговля не может быть доступна, если исполнение сделок недоступно."
            )

        if self.futures_trading_enabled and not self.trade_execution_enabled:
            errors["futures_trading_enabled"] = (
                "Торговля фьючерсами не может быть доступна, если исполнение сделок недоступно."
            )

        if errors:
            raise ValidationError(errors)
