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
        help_text="Заполняется автоматически и не редактируется вручную.",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Активен",
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

    class Meta:
        verbose_name = "Провайдер"
        verbose_name_plural = "01 Провайдеры"
        ordering = ("priority", "code")
        indexes = [
            models.Index(fields=["provider_type"]),
            models.Index(fields=["is_active", "priority"]),
        ]

    def __str__(self) -> str:
        return self.get_code_display()

    def clean(self):
        super().clean()

        if self.code:
            self.code = self.code.strip().lower()

        if self.code not in PROVIDER_DEFAULTS:
            raise ValidationError({"code": "Этот провайдер не поддерживается системой."})

        if self.pk:
            old_code = (
                self.__class__.objects.filter(pk=self.pk)
                .values_list("code", flat=True)
                .first()
            )
            if old_code and old_code != self.code:
                raise ValidationError({"code": "Код провайдера нельзя менять после создания."})

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.strip().lower()

        defaults = PROVIDER_DEFAULTS.get(self.code)
        if not defaults:
            raise ValidationError({"code": "Этот провайдер не поддерживается системой."})

        self.provider_type = defaults["provider_type"]

        if not self.affiliate_url:
            self.affiliate_url = defaults["affiliate_url"]

        if self.description:
            self.description = self.description.strip()

        self.full_clean()
        super().save(*args, **kwargs)

    def get_active_credentials(self):
        return self.credentials.filter(is_active=True).order_by("priority", "created_at", "id")

    def get_default_credential(self):
        return self.get_active_credentials().first()
