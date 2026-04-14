from django.contrib import admin

from app_providers.models.provider_asset_context import ProviderAssetContext


@admin.register(ProviderAssetContext)
class ProviderAssetContextAdmin(admin.ModelAdmin):
    save_on_top = True
    empty_value_display = "—"
    list_select_related = (
        "provider",
        "asset_context",
        "asset_context__asset",
        "asset_context__context",
    )

    autocomplete_fields = (
        "provider",
        "asset_context",
    )

    list_display = (
        "provider",
        "provider_code",
        "asset_context",
        "asset_code",
        "context_code",
        "is_active",
        "deposit_enabled",
        "withdraw_enabled",
        "deposit_confirmations",
        "withdraw_confirmations",
        "updated_at",
    )
    list_display_links = (
        "provider",
        "provider_code",
    )
    list_editable = (
        "is_active",
        "deposit_enabled",
        "withdraw_enabled",
    )
    list_filter = (
        "provider",
        "is_active",
        "deposit_enabled",
        "withdraw_enabled",
        "asset_context__asset__asset_type",
        "asset_context__context__context_type",
        "created_at",
        "updated_at",
    )
    search_fields = (
        "provider__code",
        "provider_code",
        "asset_context__code",
        "asset_context__asset__code",
        "asset_context__asset__name_short",
        "asset_context__asset__name_long",
        "asset_context__context__code",
        "asset_context__context__name_short",
        "asset_context__context__name_long",
        "description",
    )
    search_help_text = (
        "Поиск по коду провайдера, внешнему коду, AssetContext, "
        "коду/названию актива, коду/названию контекста и описанию."
    )
    readonly_fields = (
        "provider_asset_context_name_short",
        "provider_asset_context_name_long",
        "created_at",
        "updated_at",
    )
    ordering = (
        "provider",
        "provider_code",
    )
    list_per_page = 50

    fieldsets = (
        (
            "Основное",
            {
                "fields": (
                    "provider",
                    "provider_code",
                    "asset_context",
                    "is_active",
                )
            },
        ),
        (
            "Каноническая сущность",
            {
                "fields": (
                    "provider_asset_context_name_short",
                    "provider_asset_context_name_long",
                )
            },
        ),
        (
            "Доступность",
            {
                "fields": (
                    "deposit_enabled",
                    "withdraw_enabled",
                )
            },
        ),
        (
            "Подтверждения",
            {
                "fields": (
                    "deposit_confirmations",
                    "withdraw_confirmations",
                )
            },
        ),
        (
            "Комиссия на ввод",
            {
                "fields": (
                    "deposit_fee_fixed",
                    "deposit_fee_percent",
                    "deposit_fee_min_amount",
                    "deposit_fee_max_amount",
                )
            },
        ),
        (
            "Комиссия на вывод",
            {
                "fields": (
                    "withdraw_fee_fixed",
                    "withdraw_fee_percent",
                    "withdraw_fee_min_amount",
                    "withdraw_fee_max_amount",
                )
            },
        ),
        (
            "Лимиты",
            {
                "fields": (
                    "deposit_min_amount",
                    "deposit_max_amount",
                    "withdraw_min_amount",
                    "withdraw_max_amount",
                )
            },
        ),
        (
            "Дополнительно",
            {
                "fields": (
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

    @admin.display(description="Asset")
    def asset_code(self, obj):
        return obj.asset_context.asset.code

    @admin.display(description="Context")
    def context_code(self, obj):
        return obj.asset_context.context.code

    @admin.display(description="Короткое название")
    def provider_asset_context_name_short(self, obj):
        return obj.asset_context.name_short

    @admin.display(description="Полное название")
    def provider_asset_context_name_long(self, obj):
        return obj.asset_context.name_long