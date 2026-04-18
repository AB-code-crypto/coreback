from django.contrib import admin, messages
from app_providers.models.provider import Provider, ProviderCode
from app_providers.services.whitebit.fetch_stats import fetch_whitebit_stats
from app_providers.services.whitebit.fetch_all_raw import fetch_whitebit_all_raw
from app_providers.services.whitebit.sync_provider_asset_contexts import (
    sync_whitebit_provider_asset_contexts_from_raw,
)
from app_providers.services.mexc.fetch_all_raw import fetch_mexc_all_raw


def _get_single_whitebit_provider(modeladmin, request, queryset):
    if queryset.count() != 1:
        modeladmin.message_user(
            request,
            "Нужно выбрать ровно одного провайдера.",
            level=messages.WARNING,
        )
        return None

    provider = queryset.first()

    if provider.code != ProviderCode.WHITEBIT:
        modeladmin.message_user(
            request,
            "Этот action пока поддерживает только WHITEBIT.",
            level=messages.WARNING,
        )
        return None

    return provider


def _get_single_provider_by_code(modeladmin, request, queryset, provider_code):
    if queryset.count() != 1:
        modeladmin.message_user(
            request,
            "Нужно выбрать ровно одного провайдера.",
            level=messages.WARNING,
        )
        return None

    provider = queryset.first()
    if provider.code != provider_code:
        modeladmin.message_user(
            request,
            f"Этот action работает только для провайдера {provider_code}.",
            level=messages.WARNING,
        )
        return None

    return provider


@admin.action(description="Заполнить ProviderAssetContext из raw JSON WhiteBIT")
def sync_provider_asset_contexts_from_raw_action(modeladmin, request, queryset):
    provider = _get_single_whitebit_provider(modeladmin, request, queryset)
    if not provider:
        return

    try:
        result = sync_whitebit_provider_asset_contexts_from_raw(provider)
    except Exception as exc:
        modeladmin.message_user(
            request,
            f"Не удалось заполнить ProviderAssetContext: {exc}",
            level=messages.ERROR,
        )
        return

    modeladmin.message_user(
        request,
        (
            "ProviderAssetContext заполнен успешно. "
            f"Создано: {result.created}, "
            f"обновлено: {result.updated}, "
            f"без изменений: {result.skipped}, "
            f"пропущено неактивных crypto-активов: {result.skipped_inactive_assets}."
        ),
        level=messages.SUCCESS,
    )


@admin.action(description="Обновить все raw JSON WhiteBIT")
def fetch_provider_all_raw(modeladmin, request, queryset):
    provider = _get_single_whitebit_provider(modeladmin, request, queryset)
    if not provider:
        return

    result = fetch_whitebit_all_raw(provider)

    if result.failed_count == 0:
        modeladmin.message_user(
            request,
            (
                f"Успешно обновлено {result.success_count}/{result.total_count} raw JSON "
                f"в storage/raw/{provider.code}/"
            ),
            level=messages.SUCCESS,
        )
        return

    failed_names = ", ".join(item.name for item in result.items if not item.success)

    modeladmin.message_user(
        request,
        (
            f"Обновлено {result.success_count}/{result.total_count} raw JSON. "
            f"Ошибки в endpoint'ах: {failed_names}"
        ),
        level=messages.WARNING,
    )


@admin.action(description="Обновить статистику WhiteBIT")
def fetch_provider_stats(modeladmin, request, queryset):
    provider = _get_single_whitebit_provider(modeladmin, request, queryset)
    if not provider:
        return

    stats = fetch_whitebit_stats(provider)

    if stats.request_status == "success":
        modeladmin.message_user(
            request,
            (
                f"Статистика обновлена: provider={provider.code}, "
                f"pairs_total={stats.pairs_total}, "
                f"available={stats.provider_is_available}."
            ),
            level=messages.SUCCESS,
        )
    else:
        modeladmin.message_user(
            request,
            (
                f"Запрос статистики завершился со статусом '{stats.request_status}'. "
                f"Ошибка: {stats.error_message or '—'}"
            ),
            level=messages.WARNING,
        )


@admin.action(description="Обновить все raw JSON MEXC")
def fetch_provider_all_raw_mexc(modeladmin, request, queryset):
    provider = _get_single_provider_by_code(
        modeladmin,
        request,
        queryset,
        ProviderCode.MEXC,
    )
    if not provider:
        return

    result = fetch_mexc_all_raw(provider)

    if result.failed_count == 0:
        modeladmin.message_user(
            request,
            (
                f"Успешно обновлено {result.success_count}/{result.total_count} raw JSON "
                f"в storage/raw/{provider.code}/"
            ),
            level=messages.SUCCESS,
        )
        return

    failed_names = ", ".join(item.name for item in result.items if not item.success)

    modeladmin.message_user(
        request,
        (
            f"Обновлено {result.success_count}/{result.total_count} raw JSON. "
            f"Ошибки в endpoint'ах: {failed_names}"
        ),
        level=messages.WARNING,
    )


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    actions = [
        fetch_provider_all_raw,
        fetch_provider_stats,
        sync_provider_asset_contexts_from_raw_action,
        fetch_provider_all_raw_mexc,
    ]
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
                "classes": ("collapse",),
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
            "Комиссии не хранятся в карточке провайдера. "
            "Они находятся в API ключах, потому что могут от них зависеть."
        )
