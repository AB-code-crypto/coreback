from django.contrib import admin, messages

from app_providers.models.provider import Provider, ProviderCode
from app_providers.services.whitebit.fetch_stats import fetch_whitebit_stats


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    actions = ["fetch_provider_stats"]
    save_on_top = True
    empty_value_display = "—"

    list_display = (
        "code",
        "provider_type",
        "priority",
        "spot_trading_enabled",
        "deposit_enabled",
        "withdraw_enabled",
        "updated_at",
    )
    list_display_links = ("code",)
    list_editable = ("priority",)
    list_filter = (
        "provider_type",
        "price_feed_enabled",
        "deposit_enabled",
        "address_generation_enabled",
        "withdraw_enabled",
        "spot_trading_enabled",
        "futures_trading_enabled",
        "updated_at",
    )
    search_fields = (
        "code",
        "affiliate_url",
        "description",
    )
    readonly_fields = (
        "provider_type",
        "provider_fees_note",
        "created_at",
        "updated_at",
    )
    ordering = ("provider_type", "code")
    list_per_page = 50

    fieldsets = (
        (
            "Основное",
            {
                "fields": (
                    "code",
                    "provider_type",
                    "priority",
                )
            },
        ),
        (
            "Функции провайдера",
            {
                "fields": (
                    "price_feed_enabled",
                    "deposit_enabled",
                    "address_generation_enabled",
                    "withdraw_enabled",
                    "otc_enabled",
                    "spot_trading_enabled",
                    "futures_trading_enabled",
                )
            },
        ),
        (
            "Комиссии",
            {
                "fields": (
                    "provider_fees_note",
                )
            },
        ),
        (
            "Дополнительно",
            {
                "fields": (
                    "affiliate_url",
                    "description",
                )
            },
        ),
        (
            "Служебная информация",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj:
            readonly_fields.append("code")
        return readonly_fields

    @admin.display(description="Примечание")
    def provider_fees_note(self, obj):
        return (
            "Комиссии не хранятся в карточке провайдера. Они находятся в API ключах потому что могут от них зависеть"
        )

    @admin.action(description="Запросить статистику (пока только WhiteBIT)")
    def fetch_provider_stats(modeladmin, request, queryset):
        success_count = 0
        skipped_count = 0

        for provider in queryset:
            if provider.code != ProviderCode.WHITEBIT:
                skipped_count += 1
                continue

            fetch_whitebit_stats(provider)
            success_count += 1

        if success_count:
            modeladmin.message_user(
                request,
                f"Статистика успешно запрошена для {success_count} провайдер(ов).",
                level=messages.SUCCESS,
            )

        if skipped_count:
            modeladmin.message_user(
                request,
                f"{skipped_count} провайдер(ов) пропущено: action пока поддерживает только WHITEBIT.",
                level=messages.WARNING,
            )
