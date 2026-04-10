from django.core.exceptions import ValidationError
from django.db import models

from app_core.models import TimestampedModel
from .provider import Provider


class ProviderCapability(TimestampedModel):
    provider = models.OneToOneField(
        Provider,
        on_delete=models.CASCADE,
        related_name="capability",
        verbose_name="Провайдер",
    )

    supports_price_feed = models.BooleanField(
        default=True,
        verbose_name="Поддерживает трансляцию цен",
        help_text=(
            "Провайдер может использоваться как источник цен. "
            "Это относится к биржам, обменникам, агрегаторам, ЦБ РФ и другим источникам котировок. "
            "Если провайдер нужен только для движения средств без получения цен, это поле можно выключить."
        ),
    )

    supports_deposit = models.BooleanField(
        default=False,
        verbose_name="Поддерживает ввод средств",
        help_text=(
            "Через этого провайдера можно принимать средства. "
            "Например: биржа, обменник, кошелёк, нода или другой платёжный/расчётный контур, "
            "на который можно завести актив."
        ),
    )

    supports_withdraw = models.BooleanField(
        default=False,
        verbose_name="Поддерживает вывод средств",
        help_text=(
            "Через этого провайдера можно отправлять средства наружу. "
            "Например: вывод с биржи, отправка с кошелька или перевод через собственную ноду."
        ),
    )

    supports_trade_execution = models.BooleanField(
        default=False,
        verbose_name="Поддерживает исполнение сделок",
        help_text=(
            "Провайдер умеет не только принимать или отправлять средства, но и выполнять сам обмен "
            "при этом комиссии включены в курс. Типичная модель работы OTC. Комиссия за обмен здесь не добавляется."
        ),
    )

    supports_spot_trading = models.BooleanField(
        default=False,
        verbose_name="Поддерживает спот",
        help_text=(
            "Провайдер поддерживает спотовую торговлю или спотовый обмен. "
            "Если поле включено, то исполнение сделок тоже должно быть включено."
        ),
    )

    supports_futures_trading = models.BooleanField(
        default=False,
        verbose_name="Поддерживает фьючерсы",
        help_text=(
            "Провайдер поддерживает торговлю фьючерсами. "
            "Если поле включено, то исполнение сделок тоже должно быть включено."
        ),
    )

    supports_address_generation = models.BooleanField(
        default=False,
        verbose_name="Поддерживает генерацию адресов",
        help_text=(
            "Можно ли автоматически получать адрес для пополнения через этого провайдера. "
            "Это поле относится именно к генерации или выдаче депозитного адреса, а не просто "
            "к факту, что провайдер умеет принимать средства."
        ),
    )

    description = models.TextField(
        blank=True,
        verbose_name="Описание",
        help_text="Свободный комментарий или заметка для администратора.",
    )

    class Meta:
        verbose_name = "Настройки"
        verbose_name_plural = "03 Настройки"

    def __str__(self) -> str:
        return self.provider.code

    def clean(self):
        errors = {}

        has_trading_mode = self.supports_spot_trading or self.supports_futures_trading

        if has_trading_mode and not self.supports_trade_execution:
            errors["supports_trade_execution"] = (
                "Если включён спот или фьючерсы, то провайдер должен поддерживать исполнение сделок."
            )

        if self.supports_address_generation and not self.supports_deposit:
            errors["supports_address_generation"] = (
                "Генерация адресов возможна только если провайдер поддерживает ввод средств."
            )

        if errors:
            raise ValidationError(errors)
