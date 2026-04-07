from django.core.exceptions import ValidationError
from django.db import models

from app_core.models import UUIDTimestampedModel


class AssetType(models.TextChoices):
    CRYPTO = "crypto", "Крипта"
    FIAT = "fiat", "Фиат"
    OTHER = "other", "Другое"


class Asset(UUIDTimestampedModel):
    code = models.CharField(
        max_length=32,
        unique=True,
        db_index=True,
        verbose_name="Код",
        help_text="Стабильный системный код актива, например: BTC, ETH, USDT, USD.",
    )
    name_short = models.CharField(
        max_length=64,
        verbose_name="Короткое название",
        help_text="Короткое человекочитаемое название актива, например: BTC, USDT, USD.",
    )
    name_long = models.CharField(
        max_length=255,
        verbose_name="Полное название",
        help_text="Полное человекочитаемое название актива, например: Bitcoin, Tether USD, US Dollar.",
    )
    asset_type = models.CharField(
        max_length=32,
        choices=AssetType.choices,
        default=AssetType.CRYPTO,
        db_index=True,
        verbose_name="Тип актива",
        help_text="Канонический тип актива в системе.",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Активен",
        help_text="Разрешён ли актив к использованию в системе.",
    )

    class Meta:
        verbose_name = "Актив"
        verbose_name_plural = "Активы"
        ordering = ("asset_type", "code")
        indexes = [
            models.Index(fields=["asset_type"]),
            models.Index(fields=["is_active", "asset_type"]),
        ]

    def __str__(self) -> str:
        return self.code

    def clean(self):
        super().clean()

        errors = {}

        if self.code:
            normalized_code = self.code.strip().upper()
            if " " in normalized_code:
                errors["code"] = "Код актива не должен содержать пробелы."

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
