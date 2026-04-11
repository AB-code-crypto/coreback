from django.db import models

from app_core.models import TimestampedModel
from app_providers.models.provider import Provider


class ProviderStats(TimestampedModel):
    provider = models.OneToOneField(
        Provider,
        on_delete=models.CASCADE,
        related_name="stat",
        verbose_name="Провайдер",
    )
    last_calculated_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Дата последнего расчёта",
        help_text="Когда статистика по провайдеру была рассчитана в последний раз.",
    )
    pairs_total = models.PositiveIntegerField(
        default=0,
        verbose_name="Всего торговых пар",
        help_text="Общее количество найденных торговых пар у провайдера.",
    )
    quote_assets_total = models.PositiveIntegerField(
        default=0,
        verbose_name="Всего quote-активов",
        help_text="Сколько разных quote-активов найдено у провайдера.",
    )
    stablecoins_total = models.PositiveIntegerField(
        default=0,
        verbose_name="Всего активных стейблкоинов",
        help_text="Сколько quote-активов из списка стейблкоинов оказалось у провайдера.",
    )
    quote_asset_counts = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Количество пар по quote-активам",
        help_text=(
            'JSON-словарь вида {"USDT": 300, "USDC": 40}. '
            "Показывает, сколько торговых пар найдено против каждого quote-актива."
        ),
    )
    stablecoin_pair_counts = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Количество пар по стейблкоинам",
        help_text=(
            'JSON-словарь вида {"USDT": 300, "USDC": 40}. '
            "Содержит только те quote-активы, которые попали в список стейблкоинов."
        ),
    )
    active_stablecoins = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Активные стейблкоины",
        help_text=(
            'JSON-список вида ["USDT", "USDC"]. '
            "Стейблкоины отсортированы по убыванию количества торговых пар."
        ),
    )

    class Meta:
        verbose_name = "Статистика"
        verbose_name_plural = "03 Статистика"

    def __str__(self) -> str:
        return self.provider.code
