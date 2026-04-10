from django.core.validators import MinValueValidator
from django.db import models
from app_core.models import UUIDTimestampedModel


class ProviderType(models.TextChoices):
    EXCHANGE = "exchange", "Exchange"
    OTC = "otc", "OTC"
    WALLET = "wallet", "Wallet"
    BLOCKCHAIN = "blockchain", "Blockchain"
    INTERNAL = "internal", "Internal"
    OTHER = "other", "Other"


class Provider(UUIDTimestampedModel):
    code = models.SlugField(
        max_length=64,
        unique=True,
        verbose_name="Код",
        help_text="Стабильный системный код провайдера, например: binance, bybit, okx.",
    )
    name = models.CharField(
        max_length=255,
        verbose_name="Название",
        help_text="Человекочитаемое название провайдера.",
    )
    provider_type = models.CharField(
        max_length=32,
        choices=ProviderType.choices,
        default=ProviderType.EXCHANGE,
        db_index=True,
        verbose_name="Тип провайдера",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Активен",
        help_text="Глобальный административный флаг. Разрешён ли провайдер к использованию в системе вообще.",
    )
    priority = models.PositiveIntegerField(
        default=100,
        validators=[MinValueValidator(1)],
        db_index=True,
        verbose_name="Приоритет",
        help_text="Чем меньше число, тем выше приоритет провайдера.",
    )
    affiliate_url = models.URLField(
        blank=True,
        verbose_name="Партнёрская ссылка",
        help_text="Реферальная ссылка на регистрацию у провайдера для подключённых обменников.",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Описание",
        help_text="Свободный комментарий или заметка для администратора.",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Метаданные",
        help_text="Технические или дополнительные данные о провайдере в JSON-формате.",
    )

    class Meta:
        verbose_name = "Провайдер"
        verbose_name_plural = "01 Провайдеры"
        ordering = ["priority", "name"]
        indexes = [
            models.Index(fields=["provider_type"], name="prov_type_idx"),
            models.Index(fields=["is_active", "priority"], name="prov_active_prio_idx"),
        ]

    def __str__(self) -> str:
        return self.code

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.strip().lower()
        if self.name:
            self.name = self.name.strip()
        super().save(*args, **kwargs)
