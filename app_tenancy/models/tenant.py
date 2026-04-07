from django.core.exceptions import ValidationError
from django.db import models

from app_core.models import UUIDTimestampedModel


class TenantLicenseType(models.TextChoices):
    DEMO = "demo", "Демо доступ"
    PURCHASED = "purchased", "Купил лицензию"
    RENTED = "rented", "Арендует лицензию"


class Tenant(UUIDTimestampedModel):
    code = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        verbose_name="Код",
        help_text="Уникальный короткий код tenant-а для внутренней идентификации.",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Активен",
        help_text="Разрешён ли tenant-у доступ к ядру.",
    )
    license_type = models.CharField(
        max_length=32,
        choices=TenantLicenseType.choices,
        default=TenantLicenseType.RENTED,
        db_index=True,
        verbose_name="Тип лицензии",
        help_text="Тип доступа tenant-а к ядру.",
    )
    license_until = models.DateField(
        blank=True,
        null=True,
        verbose_name="Лицензия действует до",
        help_text=(
            "Срок действия лицензии. Обычно используется для демо-доступа "
            "или аренды. Для бессрочно купленной лицензии можно оставить пустым."
        ),
    )
    allowed_ip_ranges = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Разрешённые IP/CIDR",
        help_text=(
            'Список разрешённых IP или CIDR, например: ["1.2.3.4/32", "5.6.7.0/24"]. '
            "Если список пуст, доступ запрещён."
        ),
    )
    description = models.TextField(
        blank=True,
        verbose_name="Описание",
        help_text="Свободный комментарий или заметка для администратора.",
    )

    class Meta:
        verbose_name = "Арендатор"
        verbose_name_plural = "Арендаторы"
        ordering = ("code",)

    def __str__(self) -> str:
        return self.code

    def clean(self):
        super().clean()

        errors = {}

        if self.license_type in {TenantLicenseType.DEMO, TenantLicenseType.RENTED} and not self.license_until:
            errors["license_until"] = (
                "Укажите срок действия лицензии для демо-доступа или аренды."
            )

        if self.license_type == TenantLicenseType.PURCHASED and self.license_until:
            errors["license_until"] = (
                "Для купленной лицензии срок обычно не указывается."
            )

        if not self.allowed_ip_ranges:
            errors["allowed_ip_ranges"] = (
                "Укажите хотя бы один разрешённый IP или CIDR."
            )

        if errors:
            raise ValidationError(errors)
