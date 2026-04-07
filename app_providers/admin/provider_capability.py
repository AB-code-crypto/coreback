from django.contrib import admin

from app_providers.models.provider_capability import ProviderCapability


@admin.register(ProviderCapability)
class ProviderCapabilityAdmin(admin.ModelAdmin):
    save_on_top = True
    list_display = (
        "provider",
        "supports_price_feed",
        "supports_deposit",
        "supports_withdraw",
        "supports_trade_execution",
        "supports_spot_trading",
        "supports_futures_trading",
        "created_at",
        "updated_at",
    )
    list_display_links = ("provider",)
    list_editable = (
        "supports_price_feed",
        "supports_deposit",
        "supports_withdraw",
        "supports_trade_execution",
        "supports_spot_trading",
        "supports_futures_trading",
    )
    list_filter = (
        "supports_price_feed",
        "supports_deposit",
        "supports_withdraw",
        "updated_at",
    )
    search_fields = ("provider__code", "provider__name", "description")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("provider",)
    list_per_page = 50

    fieldsets = (
        (
            "Основное",
            {
                "fields": ("provider",),
            },
        ),
        (
            "Возможности провайдера",
            {
                "fields": (
                    "supports_price_feed",
                    "supports_deposit",
                    "supports_address_generation",
                    "supports_withdraw",
                    "supports_trade_execution",
                    "supports_spot_trading",
                    "supports_futures_trading",
                ),
                "description": (
                    "Здесь задаётся, что провайдер умеет в принципе. "
                    "Трансляция цен — это получение котировок. "
                    "Ввод и вывод — это движение средств через провайдера. "
                    "Исполнение сделок — это сам обмен или торговая операция. "
                    "Спот и фьючерсы уточняют, какой именно тип торговли поддерживается."
                ),
            },
        ),
        (
            "Дополнительно",
            {
                "fields": (
                    "description",
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )
