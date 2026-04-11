from django.contrib import admin

from app_providers.models.provider_status import ProviderStatus


@admin.register(ProviderStatus)
class ProviderStatusAdmin(admin.ModelAdmin):
    save_on_top = True
    empty_value_display = "—"
    list_select_related = ("provider",)

    list_display = (
        "provider",
        "status",
        "price_feed_enabled",
        "deposit_enabled",
        "address_generation_enabled",
        "withdraw_enabled",
        "trade_execution_enabled",
        "spot_trading_enabled",
        "futures_trading_enabled",
        "last_success_at",
        "last_error_at",
        "updated_at",
    )
    list_display_links = ("provider",)
    list_editable = (
        "status",
        "price_feed_enabled",
        "deposit_enabled",
        "address_generation_enabled",
        "withdraw_enabled",
        "trade_execution_enabled",
        "spot_trading_enabled",
        "futures_trading_enabled",
    )
    list_filter = (
        "status",
        "price_feed_enabled",
        "deposit_enabled",
        "address_generation_enabled",
        "withdraw_enabled",
        "trade_execution_enabled",
        "spot_trading_enabled",
        "futures_trading_enabled",
        "last_success_at",
        "last_error_at",
        "created_at",
        "updated_at",
    )
    search_fields = (
        "provider__code",
        "provider__name",
        "last_error_message",
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
                    "status",
                ),
            },
        ),
        (
            "Текущее состояние функций",
            {
                "fields": (
                    "price_feed_enabled",
                    "deposit_enabled",
                    "address_generation_enabled",
                    "withdraw_enabled",
                    "trade_execution_enabled",
                    "spot_trading_enabled",
                    "futures_trading_enabled",
                ),
                "description": (
                    "Здесь указывается, что у провайдера реально доступно прямо сейчас. "
                    "Это не постоянные возможности провайдера, а текущее operational-состояние. "
                    "Например, провайдер может в принципе поддерживать вывод средств, "
                    "но в данный момент вывод может быть временно недоступен."
                ),
            },
        ),
        (
            "События и ошибки",
            {
                "fields": (
                    "last_success_at",
                    "last_error_at",
                    "last_error_message",
                ),
                "description": (
                    "Служебная информация о последнем успешном доступе и последней зафиксированной ошибке."
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