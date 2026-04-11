from django.contrib import admin
from app_providers.models.provider_stats import ProviderStats


@admin.register(ProviderStats)
class ProviderStatsAdmin(admin.ModelAdmin):
    save_on_top = True
    empty_value_display = "—"
    list_select_related = ("provider",)

    list_display = (
        "provider",
        "pairs_total",
        "quote_assets_total",
        "stablecoins_total",
        "last_calculated_at",
        "updated_at",
    )
    list_display_links = ("provider",)
    list_filter = (
        "last_calculated_at",
        "updated_at",
    )
    search_fields = (
        "provider__code",
        "provider__name",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    ordering = ("provider",)
    list_per_page = 50

    fieldsets = (
        (
            "Основное",
            {
                "fields": (
                    "provider",
                    "last_calculated_at",
                ),
            },
        ),
        (
            "Сводные показатели",
            {
                "fields": (
                    "pairs_total",
                    "quote_assets_total",
                    "stablecoins_total",
                ),
                "description": (
                    "Это агрегированные показатели, рассчитанные по данным провайдера: "
                    "общее количество торговых пар, число разных quote-активов и число "
                    "активных стейблкоинов."
                ),
            },
        ),
        (
            "Детализация",
            {
                "fields": (
                    "quote_asset_counts",
                    "stablecoin_pair_counts",
                    "active_stablecoins",
                ),
                "description": (
                    "Здесь хранится вычисленная статистика в JSON-формате: количество пар "
                    "по quote-активам, количество пар по стейблкоинам и итоговый список "
                    "активных стейблкоинов в порядке убывания значимости."
                ),
            },
        ),
        (
            "Служебная информация",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )
