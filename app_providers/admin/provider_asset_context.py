from django.contrib import admin

from app_core.utils.decimal_format import format_decimal_for_admin
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
        "reserve_current_display",
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
        "cluster_no",
        "status_note",
        "description",
    )
    readonly_fields = (
        "deposit_fee_fixed_display",
        "deposit_fee_percent_display",
        "deposit_fee_min_amount_display",
        "deposit_fee_max_amount_display",
        "withdraw_fee_fixed_display",
        "withdraw_fee_percent_display",
        "withdraw_fee_min_amount_display",
        "withdraw_fee_max_amount_display",
        "deposit_min_amount_display",
        "deposit_max_amount_display",
        "withdraw_min_amount_display",
        "withdraw_max_amount_display",
        "reserve_current_display",
        "reserve_min_display",
        "reserve_max_display",
        "created_at",
        "updated_at",
        "AD",
        "AW",
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
                    "status_note",
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
                    "deposit_fee_fixed_display",
                    "deposit_fee_percent",
                    "deposit_fee_percent_display",
                    "deposit_fee_min_amount",
                    "deposit_fee_min_amount_display",
                    "deposit_fee_max_amount",
                    "deposit_fee_max_amount_display",
                )
            },
        ),
        (
            "Комиссия на вывод",
            {
                "fields": (
                    "withdraw_fee_fixed",
                    "withdraw_fee_fixed_display",
                    "withdraw_fee_percent",
                    "withdraw_fee_percent_display",
                    "withdraw_fee_min_amount",
                    "withdraw_fee_min_amount_display",
                    "withdraw_fee_max_amount",
                    "withdraw_fee_max_amount_display",
                )
            },
        ),
        (
            "Лимиты",
            {
                "fields": (
                    "deposit_min_amount",
                    "deposit_min_amount_display",
                    "deposit_max_amount",
                    "deposit_max_amount_display",
                    "withdraw_min_amount",
                    "withdraw_min_amount_display",
                    "withdraw_max_amount",
                    "withdraw_max_amount_display",
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
                    "reserve_current_display",
                    "reserve_min",
                    "reserve_min_display",
                    "reserve_max",
                    "reserve_max_display",
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

    @admin.display(description="Фикс. комиссия на ввод")
    def deposit_fee_fixed_display(self, obj):
        return format_decimal_for_admin(obj.deposit_fee_fixed)

    @admin.display(description="Комиссия на ввод, %")
    def deposit_fee_percent_display(self, obj):
        return format_decimal_for_admin(obj.deposit_fee_percent)

    @admin.display(description="Мин. комиссия на ввод")
    def deposit_fee_min_amount_display(self, obj):
        return format_decimal_for_admin(obj.deposit_fee_min_amount)

    @admin.display(description="Макс. комиссия на ввод")
    def deposit_fee_max_amount_display(self, obj):
        return format_decimal_for_admin(obj.deposit_fee_max_amount)

    @admin.display(description="Фикс. комиссия на вывод")
    def withdraw_fee_fixed_display(self, obj):
        return format_decimal_for_admin(obj.withdraw_fee_fixed)

    @admin.display(description="Комиссия на вывод, %")
    def withdraw_fee_percent_display(self, obj):
        return format_decimal_for_admin(obj.withdraw_fee_percent)

    @admin.display(description="Мин. комиссия на вывод")
    def withdraw_fee_min_amount_display(self, obj):
        return format_decimal_for_admin(obj.withdraw_fee_min_amount)

    @admin.display(description="Макс. комиссия на вывод")
    def withdraw_fee_max_amount_display(self, obj):
        return format_decimal_for_admin(obj.withdraw_fee_max_amount)

    @admin.display(description="Мин. сумма ввода")
    def deposit_min_amount_display(self, obj):
        return format_decimal_for_admin(obj.deposit_min_amount)

    @admin.display(description="Макс. сумма ввода")
    def deposit_max_amount_display(self, obj):
        return format_decimal_for_admin(obj.deposit_max_amount)

    @admin.display(description="Мин. сумма вывода")
    def withdraw_min_amount_display(self, obj):
        return format_decimal_for_admin(obj.withdraw_min_amount)

    @admin.display(description="Макс. сумма вывода")
    def withdraw_max_amount_display(self, obj):
        return format_decimal_for_admin(obj.withdraw_max_amount)

    @admin.display(description="Текущий резерв")
    def reserve_current_display(self, obj):
        return format_decimal_for_admin(obj.reserve_current)

    @admin.display(description="Мин. резерв")
    def reserve_min_display(self, obj):
        return format_decimal_for_admin(obj.reserve_min)

    @admin.display(description="Макс. резерв")
    def reserve_max_display(self, obj):
        return format_decimal_for_admin(obj.reserve_max)
