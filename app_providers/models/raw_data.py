from django.db import models

from app_core.models import UUIDTimestampedModel
from app_providers.models.provider import Provider


class RawRequestType(models.TextChoices):
    STATUS = "status", "Статус"
    RATES = "rates", "Котировки"
    ASSETS = "assets", "Активы"
    OTHER = "other", "Другое"


class RawRequestStatus(models.TextChoices):
    SUCCESS = "success", "Успешно"
    FAILED = "failed", "Ошибка"


class RawData(UUIDTimestampedModel):
    provider = models.ForeignKey(
        Provider,
        on_delete=models.CASCADE,
        related_name="raw_data",
        verbose_name="Провайдер",
    )
    request_type = models.CharField(
        max_length=32,
        choices=RawRequestType.choices,
        db_index=True,
        verbose_name="Тип запроса",
        help_text="Тип полученных сырых данных от провайдера.",
    )
    request_status = models.CharField(
        max_length=32,
        choices=RawRequestStatus.choices,
        default=RawRequestStatus.SUCCESS,
        db_index=True,
        verbose_name="Статус запроса",
        help_text="Результат выполнения запроса к провайдеру.",
    )
    source = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        verbose_name="Источник",
        help_text="Имя endpoint, path или служебное обозначение источника данных.",
    )
    http_status = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="HTTP статус",
        help_text="HTTP статус ответа, если запрос выполнялся по HTTP.",
    )
    requested_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Запрошено",
        help_text="Когда был отправлен запрос к провайдеру.",
    )
    responded_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Получен ответ",
        help_text="Когда был получен ответ от провайдера.",
    )
    file_path = models.CharField(
        max_length=500,
        verbose_name="Путь к файлу",
        help_text="Путь к сохранённому JSON-файлу с raw-ответом.",
    )

    is_processed = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Обработан",
        help_text="Был ли raw-ответ уже разобран и обработан.",
    )
    processing_error = models.TextField(
        blank=True,
        verbose_name="Ошибка обработки",
        help_text="Текст ошибки, если обработка raw-ответа завершилась неуспешно.",
    )

    class Meta:
        verbose_name = "Сырые данные"
        verbose_name_plural = "06 Сырые данные"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["provider", "request_type"]),
            models.Index(fields=["provider", "request_status"]),
            models.Index(fields=["provider", "is_processed"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "request_type"],
                name="unique_raw_data_per_provider_and_request_type",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.provider.code} | {self.request_type} | {self.created_at:%Y-%m-%d %H:%M:%S}"
