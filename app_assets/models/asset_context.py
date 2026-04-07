from django.core.exceptions import ValidationError
from django.db import models

from app_core.models import UUIDTimestampedModel


class AssetContext(UUIDTimestampedModel):
    asset = models.ForeignKey(
        "app_assets.Asset",
        on_delete=models.CASCADE,
        related_name="asset_contexts",
        verbose_name="Актив",
        help_text="Канонический актив.",
    )
    context = models.ForeignKey(
        "app_assets.Context",
        on_delete=models.CASCADE,
        related_name="asset_contexts",
        verbose_name="Контекст",
        help_text="Уточняющий контекст актива.",
    )
    code = models.CharField(
        max_length=128,
        unique=True,
        db_index=True,
        editable=False,
        verbose_name="Код",
        help_text="Автоматически формируемый код связки вида ASSET__CONTEXT.",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Активна",
        help_text="Разрешена ли эта связка актива и контекста к использованию в системе.",
    )

    class Meta:
        verbose_name = "Связка актива и контекста"
        verbose_name_plural = "Связки активов и контекстов"
        ordering = ("asset__code", "context__code")
        constraints = [
            models.UniqueConstraint(
                fields=["asset", "context"],
                name="unique_asset_context_pair",
            ),
        ]
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["asset", "is_active"]),
            models.Index(fields=["context", "is_active"]),
        ]

    def __str__(self) -> str:
        return self.code

    @staticmethod
    def build_code(asset_code: str, context_code: str) -> str:
        return f"{asset_code}__{context_code}"

    @property
    def name_short(self) -> str:
        return f"{self.asset.name_short} {self.context.name_short}"

    @property
    def name_long(self) -> str:
        return f"{self.asset.name_long} ({self.context.name_long})"

    def clean(self):
        super().clean()

        errors = {}

        if not self.asset_id:
            errors["asset"] = "Нужно выбрать актив."

        if not self.context_id:
            errors["context"] = "Нужно выбрать контекст."

        if self.asset_id and self.context_id:
            generated_code = self.build_code(self.asset.code, self.context.code)

            qs = self.__class__.objects.filter(code=generated_code)
            if self.pk:
                qs = qs.exclude(pk=self.pk)

            if qs.exists():
                errors["context"] = "Такая связка актива и контекста уже существует."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.asset_id and self.context_id:
            self.code = self.build_code(self.asset.code, self.context.code)

        super().save(*args, **kwargs)
