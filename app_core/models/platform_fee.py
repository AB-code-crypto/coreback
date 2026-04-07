from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from app_core.models import TimestampedModel


class PlatformFee(TimestampedModel):
    min_amount = models.PositiveBigIntegerField(
        verbose_name="Сумма от",
        help_text="Нижняя граница диапазона в USDT, включительно.",
    )
    max_amount = models.PositiveBigIntegerField(
        blank=True,
        null=True,
        verbose_name="Сумма до",
        help_text=(
            "Верхняя граница диапазона в USDT, не включительно. "
            "Если не указана, диапазон считается открытым сверху."
        ),
    )
    fee_percent = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=Decimal("1.0000"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Комиссия, %",
        help_text="Комиссия платформы в процентах. Пример: 1.5 = 1.5%, 0.75 = 0.75%.",
    )

    class Meta:
        verbose_name = "Комиссия платформы"
        verbose_name_plural = "Комиссии платформы"
        ordering = ("min_amount",)

    def __str__(self) -> str:
        if self.max_amount is None:
            return f"От {self.min_amount} → {self.fee_percent}%"
        return f"От {self.min_amount} до {self.max_amount} → {self.fee_percent}%"

    def clean(self):
        super().clean()

        errors = {}

        if self.max_amount is not None and self.max_amount <= self.min_amount:
            errors["max_amount"] = "Верхняя граница должна быть больше нижней."

        other_rows = PlatformFee.objects.exclude(pk=self.pk).order_by("min_amount")

        for row in other_rows:
            self_max = self.max_amount
            row_max = row.max_amount

            intersects = (
                    (self_max is None or row.min_amount < self_max)
                    and (row_max is None or self.min_amount < row_max)
            )

            if intersects:
                raise ValidationError("Диапазоны комиссий не должны пересекаться.")

        all_rows = list(other_rows) + [self]
        all_rows.sort(key=lambda x: x.min_amount)

        if all_rows:
            first = all_rows[0]
            if first.min_amount != 0:
                raise ValidationError(
                    {"min_amount": "Первый диапазон должен начинаться с 0."}
                )

            open_ended_seen = False

            for index, row in enumerate(all_rows):
                if open_ended_seen:
                    raise ValidationError(
                        "После открытого диапазона сверху не должно быть других диапазонов."
                    )

                if row.max_amount is None:
                    open_ended_seen = True
                    continue

                if index + 1 < len(all_rows):
                    next_row = all_rows[index + 1]
                    if row.max_amount != next_row.min_amount:
                        raise ValidationError(
                            "Между диапазонами комиссий не должно быть дыр или разрывов."
                        )
