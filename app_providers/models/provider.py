from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from app_core.models import UUIDTimestampedModel


class ProviderType(models.TextChoices):
    EXCHANGE = "exchange", "Биржа"
    OTC = "otc", "OTC"
    WALLET = "wallet", "Кошелёк"
    BLOCKCHAIN = "blockchain", "Блокчейн"
    OTHER = "other", "Другое"


class ProviderCode(models.TextChoices):
    WHITEBIT = "whitebit", "WhiteBIT"
    MEXC = "mexc", "MEXC"
    BYBIT = "bybit", "Bybit"
    BINANCE = "binance", "Binance"


PROVIDER_DEFAULTS = {
    ProviderCode.WHITEBIT: {
        "provider_type": ProviderType.EXCHANGE,
        "affiliate_url": "https://whitebit.com/ref/your-ref-code",
    },
    ProviderCode.MEXC: {
        "provider_type": ProviderType.EXCHANGE,
        "affiliate_url": "",
    },
    ProviderCode.BYBIT: {
        "provider_type": ProviderType.EXCHANGE,
        "affiliate_url": "",
    },
    ProviderCode.BINANCE: {
        "provider_type": ProviderType.EXCHANGE,
        "affiliate_url": "",
    },
}


class Provider(UUIDTimestampedModel):
    code = models.CharField(
        max_length=64,
        choices=ProviderCode.choices,
        unique=True,
        db_index=True,
        verbose_name="Провайдер",
        help_text="Выберите одного из поддерживаемых провайдеров.",
    )
    provider_type = models.CharField(
        max_length=32,
        choices=ProviderType.choices,
        editable=False,
        db_index=True,
        verbose_name="Тип провайдера",
    )
    priority = models.PositiveIntegerField(
        default=100,
        validators=[MinValueValidator(1)],
        db_index=True,
        verbose_name="Приоритет",
        help_text="Чем меньше число, тем выше приоритет.",
    )
    affiliate_url = models.URLField(
        blank=True,
        verbose_name="Партнёрская ссылка",
        help_text="Подставляется автоматически, но при необходимости можно изменить вручную.",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Описание",
    )

    price_feed_enabled = models.BooleanField(
        default=False,
        verbose_name="Трансляция цен доступна",
        help_text=(
            "Провайдер может использоваться как источник цен. "
            "Это относится к биржам, обменникам, агрегаторам, ЦБ РФ и другим источникам котировок. "
            "Если провайдер нужен только для движения средств без получения цен, это поле можно выключить."
        ),
    )
    deposit_enabled = models.BooleanField(
        default=False,
        verbose_name="Ввод средств доступен",
        help_text=(
            "Через этого провайдера можно принимать средства. "
            "Например: биржа, обменник, кошелёк, нода или другой платёжный/расчётный контур, "
            "на который можно завести актив."
        ),
    )
    address_generation_enabled = models.BooleanField(
        default=False,
        verbose_name="Генерация адресов доступна",
        help_text=(
            "Можно ли автоматически получать адрес для пополнения через этого провайдера. "
            "Это поле относится именно к генерации или выдаче депозитного адреса, а не просто "
            "к факту, что провайдер умеет принимать средства."
        ),
    )
    withdraw_enabled = models.BooleanField(
        default=False,
        verbose_name="Вывод средств доступен",
        help_text=(
            "Через этого провайдера можно отправлять средства наружу. "
            "Например: вывод с биржи, отправка с кошелька или перевод через собственную ноду."
        ),
    )
    spot_trading_enabled = models.BooleanField(
        default=False,
        verbose_name="Спот торговля доступна",
        help_text=(
            "Провайдер поддерживает спотовую торговлю или спотовый обмен. "
            "Эта функция разрешает обмен активов на стороне провайдера"
        ),
    )
    futures_trading_enabled = models.BooleanField(
        default=False,
        verbose_name="Фьючерсы доступны",
        help_text=(
            "Провайдер поддерживает торговлю фьючерсами. "
            "Используется для хеджирования средств"
        ),
    )

    class Meta:
        verbose_name = "Провайдер"
        verbose_name_plural = "01 Провайдеры"
        ordering = ("provider_type", "code")
        indexes = [
            models.Index(fields=["provider_type"]),
        ]

    def __str__(self) -> str:
        return self.get_code_display()

    def save(self, *args, **kwargs):
        defaults = PROVIDER_DEFAULTS.get(self.code)
        if not defaults:
            raise ValidationError({"code": "Этот провайдер не поддерживается системой."})

        self.provider_type = defaults["provider_type"]

        if not self.affiliate_url:
            self.affiliate_url = defaults["affiliate_url"]

        if self.address_generation_enabled:
            self.deposit_enabled = True

        if self.description:
            self.description = self.description.strip()

        super().save(*args, **kwargs)
