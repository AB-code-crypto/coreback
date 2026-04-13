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
        help_text="Итоговый результат всего запуска статистики.",
    )
    requested_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Запрошено",
        help_text="Когда был запущен сбор статистики.",
    )
    responded_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Завершено",
        help_text="Когда сбор статистики завершился.",
    )
    provider_is_available = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Провайдер доступен",
        help_text="Итоговый флаг доступности по результатам health-check.",
    )
    error_message = models.TextField(
        blank=True,
        verbose_name="Ошибка",
        help_text="Текст ошибки, если запрос завершился неуспешно.",
    )

    ping_http_status = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Ping HTTP статус",
    )
    ping_success = models.BooleanField(
        default=False,
        verbose_name="Ping успешен",
        help_text="Удалось ли успешно выполнить ping.",
    )
    ping_response_time_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Ping latency, мс",
        help_text="Задержка ответа endpoint ping.",
    )

    platform_status_http_status = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Platform status HTTP статус",
    )
    platform_status_success = models.BooleanField(
        default=False,
        verbose_name="Статус платформы получен",
        help_text="Удалось ли успешно выполнить запрос platform/status.",
    )
    platform_status_code = models.SmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Код статуса платформы",
        help_text="Например, 1 если площадка работает.",
    )
    platform_status_response_time_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Platform status latency, мс",
        help_text="Задержка ответа endpoint platform/status.",
    )

    stats_http_status = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Stats HTTP статус",
        help_text="HTTP статус основного запроса, по которому строилась статистика рынков.",
    )
    stats_source = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        verbose_name="Источник статистики",
        help_text="Какой endpoint использовался для расчёта статистики, например /markets.",
    )
    stats_response_time_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Stats latency, мс",
        help_text="Задержка ответа основного запроса статистики.",
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
