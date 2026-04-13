from django.contrib import admin, messages

from app_providers.models.provider import Provider, ProviderCode
from app_providers.models.raw_data import RawData, RawRequestType, RawRequestStatus

from app_providers.services.whitebit.assets_preview import (
    build_preview_from_raw_file,
    save_preview_file,
)
from app_providers.services.whitebit.fetch_assets import fetch_whitebit_assets
from app_providers.services.whitebit.fetch_stats import fetch_whitebit_stats


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


@admin.action(description="Запросить статистику (пока только WhiteBIT)")
def fetch_provider_stats(modeladmin, request, queryset):
    provider = _get_single_whitebit_provider(modeladmin, request, queryset)
    if not provider:
        return

    stats = fetch_whitebit_stats(provider)

    if stats.request_status == "success":
        modeladmin.message_user(
            request,
            (
                f"Статистика получена: provider={provider.code}, "
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


@admin.action(description="Получить raw assets (пока только WhiteBIT)")
def fetch_provider_assets_raw(modeladmin, request, queryset):
    provider = _get_single_whitebit_provider(modeladmin, request, queryset)
    if not provider:
        return

    raw_data = fetch_whitebit_assets(provider)

    if raw_data.request_status == RawRequestStatus.SUCCESS:
        modeladmin.message_user(
            request,
            (
                f"Raw assets получены успешно: "
                f"id={raw_data.id}, file={raw_data.file_path}"
            ),
            level=messages.SUCCESS,
        )
    else:
        modeladmin.message_user(
            request,
            (
                f"Raw assets получены с ошибкой: "
                f"id={raw_data.id}, file={raw_data.file_path}, "
                f"error={raw_data.processing_error or '—'}"
            ),
            level=messages.WARNING,
        )


@admin.action(description="Построить preview assets (пока только WhiteBIT)")
def preview_provider_assets_raw(modeladmin, request, queryset):
    provider = _get_single_whitebit_provider(modeladmin, request, queryset)
    if not provider:
        return

    raw_data = (
        RawData.objects.filter(
            provider=provider,
            request_type=RawRequestType.ASSETS,
            request_status=RawRequestStatus.SUCCESS,
        )
        .order_by("-created_at")
        .first()
    )

    if raw_data is None:
        modeladmin.message_user(
            request,
            "Нет успешного raw assets для этого провайдера. Сначала запусти action получения raw assets.",
            level=messages.WARNING,
        )
        return

    try:
        preview = build_preview_from_raw_file(raw_data.file_path)
        preview_file_path = save_preview_file(provider.code, preview)
    except Exception as exc:
        modeladmin.message_user(
            request,
            f"Не удалось построить preview: {exc}",
            level=messages.ERROR,
        )
        return

    summary = preview["summary"]

    modeladmin.message_user(
        request,
        (
            "Preview assets построен успешно: "
            f"file={preview_file_path}, "
            f"assets={summary['asset_candidates_total']}, "
            f"contexts={summary['context_candidates_total']}, "
            f"asset_contexts={summary['asset_context_candidates_total']}."
        ),
        level=messages.SUCCESS,
    )


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    actions = [
        fetch_provider_stats,
        fetch_provider_assets_raw,
        preview_provider_assets_raw,
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
