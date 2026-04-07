from django.core.exceptions import ValidationError
from django.db import models

from app_core.models import UUIDTimestampedModel


class ContextType(models.TextChoices):
    BLOCKCHAIN = "blockchain", "Блокчейн"
    BANK = "bank", "Банк"
    PAYMENT_SYSTEM = "payment_system", "Платёжная система"
    TRANSFER_SYSTEM = "transfer_system", "Система перевода"
    CASH = "cash", "Наличные"
    OTHER = "other", "Другое"


class Context(UUIDTimestampedModel):
    code = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        verbose_name="Код",
        help_text="Стабильный системный код контекста, например: TRC20, ERC20, CASH, SBP, TBANK.",
    )
    name_short = models.CharField(
        max_length=128,
        verbose_name="Короткое название",
        help_text="Короткое человекочитаемое название контекста, например: TRC20, Cash, СБП, Т-Банк.",
    )
    name_long = models.CharField(
        max_length=255,
        verbose_name="Полное название",
        help_text="Полное человекочитаемое название контекста, например: Tron Network, Наличные, Система быстрых платежей.",
    )
    context_type = models.CharField(
        max_length=32,
        choices=ContextType.choices,
        default=ContextType.OTHER,
        db_index=True,
        verbose_name="Тип контекста",
        help_text="Тип уточняющей второй части актива.",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Активен",
        help_text="Разрешён ли этот контекст к использованию в системе.",
    )

    class Meta:
        verbose_name = "Контекст"
        verbose_name_plural = "Контекст"
        ordering = ("context_type", "code")
        indexes = [
            models.Index(fields=["context_type"]),
            models.Index(fields=["is_active", "context_type"]),
        ]

    def __str__(self) -> str:
        return self.code

    def clean(self):
        super().clean()

        errors = {}

        if self.code:
            normalized_code = self.code.strip().upper()
            if " " in normalized_code:
                errors["code"] = "Код контекста не должен содержать пробелы."

        if self.name_short and not self.name_short.strip():
            errors["name_short"] = "Короткое название не должно быть пустым."

        if self.name_long and not self.name_long.strip():
            errors["name_long"] = "Полное название не должно быть пустым."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.strip().upper()

        if self.name_short:
            self.name_short = self.name_short.strip()

        if self.name_long:
            self.name_long = self.name_long.strip()

        super().save(*args, **kwargs)
