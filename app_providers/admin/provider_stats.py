import json

from django.contrib import admin
from django.utils.html import format_html, format_html_join
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
        "quote_asset_counts_display",
        "stablecoin_pair_counts_display",
        "fiat_codes_display",
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
                )
            },
        ),
        (
            "Детальная статистика",
            {
                "fields": (
                    "quote_asset_counts_display",
                    "stablecoin_pair_counts_display",
                    "fiat_codes_display",
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

    def _render_counts_dict(self, value):
        if not value:
            return "—"

        items = sorted(value.items(), key=lambda x: (-x[1], x[0]))

        return format_html(
            '<div style="font-size: 14px; line-height: 1.7; max-width: 1100px;">{}</div>',
            format_html_join(
                ", ",
                "<span><b>{}</b> — {}</span>",
                ((key, count) for key, count in items),
            ),
        )

    def _render_code_list(self, value):
        if not value:
            return "—"

        return format_html(
            '<div style="font-size: 14px; line-height: 1.7; max-width: 1100px;">{}</div>',
            format_html_join(
                ", ",
                "<span><b>{}</b></span>",
                ((item,) for item in value),
            ),
        )

    @admin.display(description="Количество пар по quote-активам")
    def quote_asset_counts_display(self, obj):
        return self._render_counts_dict(obj.quote_asset_counts)

    @admin.display(description="Количество пар по стейблкоинам")
    def stablecoin_pair_counts_display(self, obj):
        return self._render_counts_dict(obj.stablecoin_pair_counts)

    @admin.display(description="Фиатные валюты")
    def fiat_codes_display(self, obj):
        return self._render_code_list(obj.fiat_codes)
