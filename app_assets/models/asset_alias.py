from django.core.exceptions import ValidationError
from django.db import models

from app_core.models import UUIDTimestampedModel
from app_assets.models.asset import Asset


class AssetAlias(UUIDTimestampedModel):
    asset = models.ForeignKey(
        "app_assets.Asset",
        on_delete=models.CASCADE,
        related_name="aliases",
        verbose_name="Актив",
        help_text="Канонический актив, к которому относится этот алиас.",
    )
    code = models.CharField(
        max_length=32,
        unique=True,
        db_index=True,
        verbose_name="Код алиаса",
        help_text="Альтернативный код актива, например: XBT для BTC.",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Активен",
        help_text="Активен ли этот алиас для нормализации и поиска.",
    )

    class Meta:
        verbose_name = "Алиас актива"
        verbose_name_plural = "Алиасы активов"
        ordering = ("code",)
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["asset", "is_active"]),
        ]

    def __str__(self) -> str:
        return self.code

    def clean(self):
        super().clean()

        errors = {}

        normalized_code = ""
        if self.code:
            normalized_code = self.code.strip().upper()
            if " " in normalized_code:
                errors["code"] = "Код алиаса не должен содержать пробелы."

        if self.asset_id and normalized_code:
            if normalized_code == self.asset.code:
                errors["code"] = "Код алиаса не должен совпадать с каноническим кодом актива."

            existing_asset = Asset.objects.filter(code=normalized_code).first()
            if existing_asset:
                errors["code"] = (
                    f"Код '{normalized_code}' уже используется как канонический код актива."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.strip().upper()

        super().save(*args, **kwargs)
