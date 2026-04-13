from django.db import models

from app_core.models import UUIDTimestampedModel
from app_providers.models.provider import Provider


class ProviderStatsRequestStatus(models.TextChoices):
    SUCCESS = "success", "Успешно"
    FAILED = "failed", "Ошибка"
    TIMEOUT = "timeout", "Таймаут"


class ProviderStats(UUIDTimestampedModel):
    provider = models.ForeignKey(
        Provider,
        on_delete=models.CASCADE,
        related_name="stats",
        verbose_name="Провайдер",
    )

    request_status = models.CharField(
        max_length=32,
        choices=ProviderStatsRequestStatus.choices,
        db_index=True,
        default=ProviderStatsRequestStatus.SUCCESS,
        verbose_name="Статус запроса",
        help_text="Результат выполнения запроса статистики.",
    )
    requested_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Запрошено",
        help_text="Когда был отправлен запрос статистики.",
    )
    responded_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Получен ответ",
        help_text="Когда был получен ответ на запрос статистики.",
    )
    response_time_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Время ответа, мс",
        help_text="Сколько миллисекунд занял запрос статистики.",
    )
    http_status = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="HTTP статус",
        help_text="HTTP статус ответа, если запрос был по HTTP.",
    )
    source = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        verbose_name="Источник",
        help_text="Какой endpoint или источник использовался, например /status или /markets.",
    )
    provider_is_available = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Провайдер доступен",
        help_text="Удалось ли подтвердить доступность провайдера по этому запросу.",
    )
    error_message = models.TextField(
        blank=True,
        verbose_name="Ошибка",
        help_text="Текст ошибки, если запрос завершился неуспешно.",
    )

    pairs_total = models.PositiveIntegerField(
        default=0,
        verbose_name="Всего торговых пар",
    )
    quote_assets_total = models.PositiveIntegerField(
        default=0,
        verbose_name="Всего quote-активов",
    )
    stablecoins_total = models.PositiveIntegerField(
        default=0,
        verbose_name="Всего активных стейблкоинов",
    )

    quote_asset_counts = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Количество пар по quote-активам",
    )
    stablecoin_pair_counts = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Количество пар по стейблкоинам",
    )
    active_stablecoins = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Активные стейблкоины",
    )
    fiat_codes = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Фиатные валюты",
    )
    top_quote_assets = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Популярные quote-активы",
    )
    top_base_assets = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Популярные base-активы",
    )

    class Meta:
        verbose_name = "Статистика"
        verbose_name_plural = "03 Статистика"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.provider.code} | {self.created_at:%Y-%m-%d %H:%M:%S}"
