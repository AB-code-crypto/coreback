from django.contrib import admin

from app_providers.models.provider_asset_context import ProviderAssetContext


@admin.register(ProviderAssetContext)
class ProviderAssetContextAdmin(admin.ModelAdmin):
    save_on_top = True
    empty_value_display = "—"
    list_select_related = ("provider",)
    autocomplete_fields = ("provider",)

    list_display = (
        "provider",
        "asset_code",
        "context_code",
        "cluster_no",
        "is_front",
        "D",
        "W",
        "AD",
        "AW",
        "reserve_current",
        "updated_at",
    )
    list_display_links = (
        "provider",
        "asset_code",
        "context_code",
    )
    list_editable = (
        "cluster_no",
        "is_front",
        "D",
        "W",
    )
    list_filter = (
        "provider",
        "is_active",
        "is_front",
        "is_stablecoin",
        "D",
        "W",
        "AD",
        "AW",
        "updated_at",
    )
    search_fields = (
        "provider__code",
        "asset_code",
        "asset_name",
        "context_code",
        "context_name",
        "asset_code_pl",
        "asset_name_pl",
        "context_code_pl",
        "context_name_pl",
        "contract_raw",
        "description",
    )
    readonly_fields = (
        "AD",
        "AW",
        "created_at",
        "updated_at",
    )
    ordering = (
        "provider",
        "cluster_no",
        "asset_code",
        "context_code",
        "id",
    )
    list_per_page = 50

    fieldsets = (
        (
            "Основное",
            {
                "fields": (
                    "provider",
                    "is_active",
                    "cluster_no",
                    "is_front",
                    "match_status",
                )
            },
        ),
        (
            "Raw данные от провайдера",
            {
                "fields": (
                    "asset_code_pl",
                    "asset_name_pl",
                    "context_code_pl",
                    "context_name_pl",
                    "contract_raw",
                )
            },
        ),
        (
            "Нормализованные поля",
            {
                "fields": (
                    "asset_code",
                    "asset_name",
                    "context_code",
                    "context_name",
                )
            },
        ),
        (
            "Доступность",
            {
                "fields": (
                    "D",
                    "W",
                    "AD",
                    "AW",
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
            "Тип / точность / номинал",
            {
                "fields": (
                    "is_stablecoin",
                    "amount_precision",
                    "nominal",
                )
            },
        ),
        (
            "Резервы",
            {
                "fields": (
                    "reserve_current",
                    "reserve_min",
                    "reserve_max",
                )
            },
        ),
        (
            "Медиа / витрина",
            {
                "fields": (
                    "icon_file",
                    "icon_url",
                )
            },
        ),
        (
            "Сырые метаданные и описание",
            {
                "fields": (
                    "raw_metadata",
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
