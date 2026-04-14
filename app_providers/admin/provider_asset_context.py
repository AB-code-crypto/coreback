from django.contrib import admin

from app_providers.models.provider_asset_context import ProviderAssetContext


@admin.register(ProviderAssetContext)
class ProviderAssetContextAdmin(admin.ModelAdmin):
    save_on_top = True
    empty_value_display = "—"
    list_select_related = ("provider", "asset_context", "asset_context__asset", "asset_context__context")

    list_display = (
        "provider",
        "asset_name_short",
        "context_name_short",
        "is_active",
        "deposit_enabled",
        "withdraw_enabled",
        "updated_at",
    )
    list_display_links = ("provider", )
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
    readonly_fields = (
        "provider_asset_context_name_short",
        "provider_asset_context_name_long",
        "created_at",
        "updated_at",
    )
    ordering = ("provider", "provider_code")
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
            "Доступные операции",
            {
                "fields": (
                    "deposit_enabled",
                    "withdraw_enabled",
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

    @admin.display(description="Актив")
    def asset_name_short(self, obj):
        return obj.asset_context.asset.name_short

    @admin.display(description="Контекст")
    def context_name_short(self, obj):
        return obj.asset_context.context.name_short

    @admin.display(description="Короткое название")
    def provider_asset_context_name_short(self, obj):
        return obj.asset_context.name_short

    @admin.display(description="Полное название")
    def provider_asset_context_name_long(self, obj):
        return obj.asset_context.name_long
