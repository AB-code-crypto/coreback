from django.contrib import admin, messages
from django import forms

from app_providers.models.provider import ProviderCode
from app_providers.models.provider_api import ProviderApi
from app_providers.services.whitebit.sync_provider_api_fees import (
    sync_whitebit_provider_api_fees,
)


class ProviderApiAdminForm(forms.ModelForm):
    new_api_key = forms.CharField(
        required=False,
        label="Новый API Key",
        widget=forms.PasswordInput(render_value=False),
        help_text='Поле для: Api public, Api key, Публичный ключ. Для Rapira.net сюда надо ввести UID',
    )
    clear_api_key = forms.BooleanField(
        required=False,
        label="Очистить API Key",
    )

    new_api_secret = forms.CharField(
        required=False,
        label="Новый API Secret",
        widget=forms.PasswordInput(render_value=False),
        help_text='Поле для: Api secret, Api private',
    )
    clear_api_secret = forms.BooleanField(
        required=False,
        label="Очистить API Secret",
    )

    new_api_passphrase = forms.CharField(
        required=False,
        label="Новый API Passphrase",
        widget=forms.PasswordInput(render_value=False),
        help_text='Используется редко. Нужно для OKX, Kucoin',
    )
    clear_api_passphrase = forms.BooleanField(
        required=False,
        label="Очистить API Passphrase",
    )

    new_broker_key = forms.CharField(
        required=False,
        label="Новый Broker Key",
        widget=forms.PasswordInput(render_value=False),
        help_text='Api key для брокера',
    )
    clear_broker_key = forms.BooleanField(
        required=False,
        label="Очистить Broker Key",
    )

    new_trade_password = forms.CharField(
        required=False,
        label="Новый Trade Password",
        widget=forms.PasswordInput(render_value=False),
        help_text='Используется редко для отдельного торгового пароля. Есть на Kucoin',
    )
    clear_trade_password = forms.BooleanField(
        required=False,
        label="Очистить Trade Password",
    )


@admin.action(description="Обновить торговые комиссии WhiteBIT")
def update_whitebit_trading_fees(modeladmin, request, queryset):
    updated_count = 0
    unchanged_count = 0
    skipped_count = 0
    error_messages: list[str] = []

    for provider_api in queryset.select_related("provider"):
        if provider_api.provider.code != ProviderCode.WHITEBIT:
            skipped_count += 1
            continue

        try:
            result = sync_whitebit_provider_api_fees(provider_api)
        except Exception as exc:
            error_messages.append(
                f"{provider_api.provider.code} / {provider_api.name}: {exc}"
            )
            continue

        if result.updated:
            updated_count += 1
        else:
            unchanged_count += 1

    if updated_count:
        modeladmin.message_user(
            request,
            (
                f"Торговые комиссии обновлены: {updated_count}. "
                f"Без изменений: {unchanged_count}. "
                f"Пропущено: {skipped_count}."
            ),
            level=messages.SUCCESS,
        )
    else:
        modeladmin.message_user(
            request,
            (
                f"Ничего не обновлено. "
                f"Без изменений: {unchanged_count}. "
                f"Пропущено: {skipped_count}."
            ),
            level=messages.WARNING,
        )

    for msg in error_messages[:10]:
        modeladmin.message_user(request, msg, level=messages.ERROR)

    if len(error_messages) > 10:
        modeladmin.message_user(
            request,
            f"Ещё ошибок: {len(error_messages) - 10}",
            level=messages.ERROR,
        )


@admin.register(ProviderApi)
class ProviderApiAdmin(admin.ModelAdmin):
    actions = [update_whitebit_trading_fees]
    save_on_top = True
    form = ProviderApiAdminForm
    empty_value_display = "—"

    list_display = (
        "provider",
        "name",
        "is_active",
        "priority",
        "spot_maker_fee",
        "spot_taker_fee",
        "updated_at",
    )
    list_display_links = ("provider", "name")
    list_editable = (
        "is_active",
        "priority",
        "spot_maker_fee",
        "spot_taker_fee",
    )
    list_filter = (
        "provider",
        "is_active",
        "is_ip_whitelist_enabled",
        "updated_at",
    )
    search_fields = (
        "provider__code",
        "name",
        "description",
    )
    readonly_fields = (
        "api_key_masked_display",
        "api_secret_masked_display",
        "api_passphrase_masked_display",
        "broker_key_masked_display",
        "trade_password_masked_display",
        "created_at",
        "updated_at",
    )
    ordering = ("provider", "priority", "created_at")
    list_per_page = 50

    fieldsets = (
        (
            "Основное",
            {
                "fields": (
                    "provider",
                    "name",
                    "is_active",
                    "priority",
                )
            },
        ),
        (
            "Комиссии",
            {
                "fields": (
                    "spot_maker_fee",
                    "spot_taker_fee",
                    "futures_maker_fee",
                    "futures_taker_fee",
                )
            },
        ),
        (
            "Текущие сохранённые значения",
            {
                "fields": (
                    "api_key_masked_display",
                    "api_secret_masked_display",
                    "api_passphrase_masked_display",
                    "broker_key_masked_display",
                    "trade_password_masked_display",
                )
            },
        ),
        (
            "Замена секретов",
            {
                "fields": (
                    ("new_api_key", "clear_api_key"),
                    ("new_api_secret", "clear_api_secret"),
                    ("new_api_passphrase", "clear_api_passphrase"),
                    ("new_broker_key", "clear_broker_key"),
                    ("new_trade_password", "clear_trade_password"),
                ),
                "description": (
                    "Оставь поле пустым, если текущее значение менять не нужно. "
                    "Отметь чекбокс, если значение нужно удалить. "
                    "Полные значения секретов никогда не показываются."
                ),
            },
        ),
        (
            "Ограничения по IP",
            {
                "fields": (
                    "is_ip_whitelist_enabled",
                    "allowed_ip_ranges",
                )
            },
        ),
        (
            "Дополнительно",
            {
                "fields": (
                    "description",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    @admin.display(description="Текущий API Key")
    def api_key_masked_display(self, obj):
        return obj.get_api_key_masked()

    @admin.display(description="Текущий API Secret")
    def api_secret_masked_display(self, obj):
        return obj.get_api_secret_masked()

    @admin.display(description="Текущий API Passphrase")
    def api_passphrase_masked_display(self, obj):
        return obj.get_api_passphrase_masked()

    @admin.display(description="Текущий Broker Key")
    def broker_key_masked_display(self, obj):
        return obj.get_broker_key_masked()

    @admin.display(description="Текущий Trade Password")
    def trade_password_masked_display(self, obj):
        return obj.get_trade_password_masked()
