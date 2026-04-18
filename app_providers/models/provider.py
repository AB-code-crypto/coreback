from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from app_core.models import UUIDTimestampedModel


class ProviderType(models.TextChoices):
    CEX = "CEX", "Классическая биржа (CEX)"
    DEX = "DEX", "Децентрализованная биржа (DEX)"
    PSP = "PSP", "Платёжная система (PSP)"
    OTC = "OTC", "OTC провайдер (OTC)"
    WALLET = "WALLET", "Кошелёк"
    NODE = "NODE", "Нода"
    EXCHANGER = "EXCHANGER", "Обменник"
    BANK = "BANK", "Банк"
    CASH = "CASH", "Наличные"
    P2P = "P2P", "P2P"
    MAINER = "MAINER", "Майнер"
    OTHER = "OTHER", "Другое"


class ProviderCode(models.TextChoices):
    # Биржи (CEX/DEX)
    WHITEBIT = "WHITEBIT", "WhiteBit"
    MEXC = "MEXC", "MEXC"
    BYBIT = "BYBIT", "ByBit"
    # BINANCE = "BINANCE", "Binance"
    # KUCOIN = "KUCOIN", "KuCoin"
    # HTX = "HTX", "HTX"
    # RAPIRA = "RAPIRA", "Rapira"
    # COINBASE_EXCHANGE = "COINBASE_EXCHANGE", "Coinbase Exchange"
    # UPBIT = "UPBIT", "Upbit"
    # BITSTAMP = "BITSTAMP", "Bitstamp"
    # BINGX = "BINGX", "BingX"
    # BITFINEX = "BITFINEX", "Bitfinex"
    # GATEIO = "GATEIO", "Gate.io"
    # BITGET = "BITGET", "Bitget"
    # OKX = "OKX", "OKX"
    # GEMINI = "GEMINI", "Gemini"
    # LBANK = "LBANK", "LBank"
    # UNISWAP = "UNISWAP", "Uniswap"
    # PANCAKESWAP = "PANCAKESWAP", "PancakeSwap"

    # Платёжные системы (PSP)
    # PAYPAL = "PAYPAL", "PayPal"
    # ADVCASH = "ADVCASH", "Advanced Cash"
    # FIREKASSA = "FIREKASSA", "FireKassa"
    # APIRONE = "APIRONE", "Apirone"

    # Обменники (EXCHANGER)
    # CHANGENOW = "CHANGENOW", "ChangeNOW"
    # CHANGELLY = "CHANGELLY", "Changelly"
    # FIXEDFLOAT = "FIXEDFLOAT", "ff.io"
    # QUICKEX = "QUICKEX", "Quickex"
    # ALFABIT = "ALFABIT", "Alfabit"

    # Кошельки (WALLET)
    # WESTWALLET = "WESTWALLET", "WestWallet"
    # TRUSTWALLET = "TRUSTWALLET", "Trust Wallet"
    # TRONWALLET = "TRONWALLET", "Tron Wallet"
    # ANTARCTICWALLET = "ANTARCTICWALLET", "Antarctic Wallet"
    # TELEGRAM_WALLET = "TELEGRAM_WALLET", "Telegram Wallet"

    # Ноды (NODE)
    # BTC_NODE = "BTC_NODE", "BTC Node"
    # XMR_NODE = "XMR_NODE", "XMR Node"
    # USDT_NODE = "USDT_NODE", "USDT Node"
    # USDC_NODE = "USDC_NODE", "USDC Node"
    # DASH_NODE = "DASH_NODE", "DASH Node"

    # Банки (BANK)
    # SBERBANK = "SBERBANK", "Сбербанк"
    # TBANK = "TBANK", "ТБанк"
    # ALFABANK = "ALFABANK", "Альфабанк"
    # VTB = "VTB", "ВТБ банк"


PROVIDER_DEFAULTS = {
    ProviderCode.WHITEBIT: {"provider_type": ProviderType.CEX, "affiliate_url": "https://whitebit.com/ru"},
    ProviderCode.MEXC: {"provider_type": ProviderType.CEX, "affiliate_url": "https://www.mexc.com"},
    # ProviderCode.BYBIT: {"provider_type": ProviderType.CEX, "affiliate_url": ""},
    # ProviderCode.BINANCE: {"provider_type": ProviderType.CEX, "affiliate_url": ""},
}


class Provider(UUIDTimestampedModel):
    code = models.CharField(max_length=64, choices=ProviderCode.choices, unique=True, db_index=True, verbose_name="Провайдер",help_text="Выберите одного из поддерживаемых провайдеров.")
    provider_type = models.CharField(max_length=32, choices=ProviderType.choices, editable=False, db_index=True, verbose_name="Тип провайдера")
    priority = models.PositiveIntegerField(default=100, validators=[MinValueValidator(1)], db_index=True, verbose_name="Приоритет",help_text="Чем меньше число, тем выше приоритет.")
    affiliate_url = models.URLField(blank=True, verbose_name="Партнёрская ссылка",help_text="Подставляется автоматически, но при необходимости можно изменить вручную.")
    description = models.TextField(blank=True, verbose_name="Описание")
    price_feed_enabled = models.BooleanField(default=False, verbose_name="Трансляция цен",help_text="Провайдер может использоваться как источник цен. Это относится к биржам, обменникам, агрегаторам, ЦБ РФ и другим источникам котировок. Если провайдер нужен только для движения средств без получения цен, это поле можно выключить.")
    deposit_enabled = models.BooleanField(default=False, verbose_name="Ввод средств",help_text="Через этого провайдера можно принимать средства. Например: биржа, обменник, кошелёк, нода или другой платёжный/расчётный контур, на который можно завести актив.")
    address_generation_enabled = models.BooleanField(default=False, verbose_name="Генерация адресов",help_text="Можно ли автоматически получать адрес для пополнения через этого провайдера. Это поле относится именно к генерации или выдаче депозитного адреса, а не просто к факту, что провайдер умеет принимать средства.")
    withdraw_enabled = models.BooleanField(default=False, verbose_name="Вывод средств",help_text="Через этого провайдера можно отправлять средства наружу. Например: вывод с биржи, отправка с кошелька или перевод через собственную ноду.")
    otc_enabled = models.BooleanField(default=False, verbose_name="ОТС обмен",help_text="Провайдер поддерживает обмен, но это не спот. Используется для ОТС рынков При ОТС обмене не применяется комиссия провайдера")
    spot_trading_enabled = models.BooleanField(default=False, verbose_name="Спот торговля",help_text="Провайдер поддерживает спотовую торговлю или спотовый обмен. Эта функция разрешает обмен активов на стороне провайдера")
    futures_trading_enabled = models.BooleanField(default=False, verbose_name="Фьючерсы",help_text="Провайдер поддерживает торговлю фьючерсами. Используется для хеджирования средств")

    class Meta:
        verbose_name = "Провайдер"
        verbose_name_plural = "01 Провайдеры"
        ordering = ("provider_type", "code")
        indexes = [models.Index(fields=["provider_type"])]

    def __str__(self) -> str:
        return self.get_code_display()

    def clean(self):
        super().clean()

        defaults = PROVIDER_DEFAULTS.get(self.code)
        if not defaults:
            raise ValidationError(
                {"code": "Для этого ProviderCode не настроены PROVIDER_DEFAULTS."}
            )

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
