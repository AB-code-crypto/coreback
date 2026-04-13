import json

from django.contrib import admin
from django.utils.html import format_html

from app_providers.models.provider_stats import ProviderStats


@admin.register(ProviderStats)
class ProviderStatsAdmin(admin.ModelAdmin):
    save_on_top = True
    empty_value_display = "—"
    list_select_related = ("provider",)
    date_hierarchy = "created_at"

    list_display = (
        "provider",
        "request_status",
        "provider_is_available",
        "ping_success",
        "ping_response_time_ms",
        "platform_status_success",
        "platform_status_code",
        "stats_response_time_ms",
        "pairs_total",
        "created_at",
    )
    list_display_links = ("provider", "created_at")
    list_filter = (
        "provider",
        "request_status",
        "provider_is_available",
        "ping_success",
        "platform_status_success",
        "platform_status_code",
        "stats_source",
        "created_at",
    )
    search_fields = (
        "provider__code",
        "stats_source",
        "error_message",
    )
    search_help_text = "Поиск по коду провайдера, источнику статистики и тексту ошибки."
    ordering = ("-created_at",)
    list_per_page = 50

    readonly_fields = (
        "provider",
        "request_status",
        "requested_at",
        "responded_at",
        "provider_is_available",
        "error_message",
        "ping_http_status",
        "ping_success",
        "ping_response_time_ms",
        "platform_status_http_status",
        "platform_status_success",
        "platform_status_code",
        "platform_status_response_time_ms",
        "stats_http_status",
        "stats_source",
        "stats_response_time_ms",
        "pairs_total",
        "quote_assets_total",
        "stablecoins_total",
        "quote_asset_counts_pretty",
        "stablecoin_pair_counts_pretty",
        "active_stablecoins_pretty",
        "fiat_codes_pretty",
        "top_quote_assets_pretty",
        "top_base_assets_pretty",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Основное",
            {
                "fields": (
                    "provider",
                    "request_status",
                    "provider_is_available",
                    "error_message",
                )
            },
        ),
        (
            "Время выполнения",
            {
                "fields": (
                    "requested_at",
                    "responded_at",
                    "created_at",
                    "updated_at",
                )
            },
        ),
        (
            "Ping",
            {
                "fields": (
                    "ping_http_status",
                    "ping_success",
                    "ping_response_time_ms",
                )
            },
        ),
        (
            "Platform Status",
            {
                "fields": (
                    "platform_status_http_status",
                    "platform_status_success",
                    "platform_status_code",
                    "platform_status_response_time_ms",
                )
            },
        ),
        (
            "Основной запрос статистики",
            {
                "fields": (
                    "stats_http_status",
                    "stats_source",
                    "stats_response_time_ms",
                )
            },
        ),
        (
            "Сводные показатели",
            {
                "fields": (
                    "pairs_total",
                    "quote_assets_total",
                    "stablecoins_total",
                )
            },
        ),
        (
            "Детальная статистика",
            {
                "fields": (
                    "quote_asset_counts_pretty",
                    "stablecoin_pair_counts_pretty",
                    "active_stablecoins_pretty",
                    "fiat_codes_pretty",
                    "top_quote_assets_pretty",
                    "top_base_assets_pretty",
                )
            },
        ),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def _pretty_json(self, value):
        if value in (None, "", {}, []):
            return "—"
        return format_html(
            "<pre style='white-space: pre-wrap; margin: 0;'>{}</pre>",
            json.dumps(value, ensure_ascii=False, indent=2),
        )

    @admin.display(description="Количество пар по quote-активам")
    def quote_asset_counts_pretty(self, obj):
        return self._pretty_json(obj.quote_asset_counts)

    @admin.display(description="Количество пар по стейблкоинам")
    def stablecoin_pair_counts_pretty(self, obj):
        return self._pretty_json(obj.stablecoin_pair_counts)

    @admin.display(description="Активные стейблкоины")
    def active_stablecoins_pretty(self, obj):
        return self._pretty_json(obj.active_stablecoins)

    @admin.display(description="Фиатные валюты")
    def fiat_codes_pretty(self, obj):
        return self._pretty_json(obj.fiat_codes)

    @admin.display(description="Популярные quote-активы")
    def top_quote_assets_pretty(self, obj):
        return self._pretty_json(obj.top_quote_assets)

    @admin.display(description="Популярные base-активы")
    def top_base_assets_pretty(self, obj):
        return self._pretty_json(obj.top_base_assets)
