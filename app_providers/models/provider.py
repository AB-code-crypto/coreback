from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from app_core.models import UUIDTimestampedModel
from app_providers.config import (
    get_supported_provider_spec,
    normalize_provider_code,
)


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
        help_text="Системный код поддерживаемого провайдера.",
    )
    name = models.CharField(
        max_length=255,
        editable=False,
        verbose_name="Название",
        help_text="Автоматически заполняется по выбранному поддерживаемому провайдеру.",
    )
    provider_type = models.CharField(
        max_length=32,
        choices=ProviderType.choices,
        db_index=True,
        editable=False,
        verbose_name="Тип провайдера",
        help_text="Автоматически заполняется по выбранному поддерживаемому провайдеру.",
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
        editable=False,
        verbose_name="Партнёрская ссылка",
        help_text="Автоматически заполняется по выбранному поддерживаемому провайдеру.",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Описание",
        help_text="Свободный комментарий или заметка для администратора.",
    )

    class Meta:
        verbose_name = "Провайдер"
        verbose_name_plural = "01 Провайдеры"
        ordering = ["priority", "name"]
        indexes = [
            models.Index(fields=["provider_type"]),
            models.Index(fields=["is_active", "priority"]),
        ]

    def __str__(self) -> str:
        return self.code

    def clean(self):
        super().clean()

        self.code = normalize_provider_code(self.code)

        spec = get_supported_provider_spec(self.code)
        if spec is None:
            raise ValidationError(
                {"code": "Этот провайдер не поддерживается системой."}
            )

    def save(self, *args, **kwargs):
        self.code = normalize_provider_code(self.code)

        spec = get_supported_provider_spec(self.code)
        if spec is None:
            raise ValidationError(
                {"code": "Этот провайдер не поддерживается системой."}
            )

        self.name = spec.name
        self.provider_type = spec.provider_type
        self.affiliate_url = spec.affiliate_url

        if self.description:
            self.description = self.description.strip()

        super().save(*args, **kwargs)

    def get_active_credentials(self):
        return self.credentials.filter(is_active=True).order_by("priority", "created_at", "id")

    def get_default_credential(self):
        return self.get_active_credentials().first()
