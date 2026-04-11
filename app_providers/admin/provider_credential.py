from django import forms
from django.contrib import admin

from app_core.utils.decimal_format import format_decimal_for_admin
from app_providers.models.provider_credential import ProviderCredential


class ProviderCredentialAdminForm(forms.ModelForm):
    new_api_key = forms.CharField(
        required=False,
        label="Новый API Key",
        widget=forms.PasswordInput(render_value=False),
    )
    new_api_secret = forms.CharField(
        required=False,
        label="Новый API Secret",
        widget=forms.PasswordInput(render_value=False),
    )
    new_api_passphrase = forms.CharField(
        required=False,
        label="Новый API Passphrase",
        widget=forms.PasswordInput(render_value=False),
    )
    new_broker_key = forms.CharField(
        required=False,
        label="Новый Broker Key",
        widget=forms.PasswordInput(render_value=False),
    )
    new_trade_password = forms.CharField(
        required=False,
        label="Новый Trade Password",
        widget=forms.PasswordInput(render_value=False),
    )

    class Meta:
        model = ProviderCredential
        fields = (
            "provider",
            "name",
            "is_active",
            "priority",
            "spot_maker_fee",
            "spot_taker_fee",
            "futures_maker_fee",
            "futures_taker_fee",
            "fees_updated_at",
            "is_ip_whitelist_enabled",
            "allowed_ip_ranges",
            "description",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        decimal_fields = (
            "spot_maker_fee",
            "spot_taker_fee",
            "futures_maker_fee",
            "futures_taker_fee",
        )

        for field_name in decimal_fields:
            value = getattr(self.instance, field_name, None)
            if value is not None:
                self.initial[field_name] = format_decimal_for_admin(value)

    def save(self, commit=True):
        obj = super().save(commit=False)

        new_api_key = self.cleaned_data.get("new_api_key")
        new_api_secret = self.cleaned_data.get("new_api_secret")
        new_api_passphrase = self.cleaned_data.get("new_api_passphrase")
        new_broker_key = self.cleaned_data.get("new_broker_key")
        new_trade_password = self.cleaned_data.get("new_trade_password")

        if new_api_key:
            obj.set_api_key(new_api_key)

        if new_api_secret:
            obj.set_api_secret(new_api_secret)

        if new_api_passphrase:
            obj.set_api_passphrase(new_api_passphrase)

        if new_broker_key:
            obj.set_broker_key(new_broker_key)

        if new_trade_password:
            obj.set_trade_password(new_trade_password)

        if commit:
            obj.save()

        return obj


@admin.register(ProviderCredential)
class ProviderCredentialAdmin(admin.ModelAdmin):
    save_on_top = True
    form = ProviderCredentialAdminForm

    list_display = (
        "provider",
        "name",
        "is_active",
        "priority",
        "spot_maker_fee_display",
        "spot_taker_fee_display",
        "futures_maker_fee_display",
        "futures_taker_fee_display",
        "fees_updated_at",
        # "has_api_key_display",
        # "has_api_secret_display",
        # "has_api_passphrase_display",
        # "has_broker_key_display",
        # "has_trade_password_display",
        "updated_at",
    )
    list_display_links = ("provider", "name")
    list_editable = ("is_active", "priority")
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
    ordering = ("is_active", "priority", "provider", "name")
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
                    "new_api_key",
                    "new_api_secret",
                    "new_api_passphrase",
                    "new_broker_key",
                    "new_trade_password",
                ),
                "description": (
                    "Оставь поле пустым, если текущее значение менять не нужно. "
                    "Полные значения секретов никогда не показываются."
                ),
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
                    "fees_updated_at",
                )
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

    @admin.display(boolean=True, description="API Key")
    def has_api_key_display(self, obj):
        return obj.has_api_key()

    @admin.display(boolean=True, description="API Secret")
    def has_api_secret_display(self, obj):
        return obj.has_api_secret()

    @admin.display(boolean=True, description="API Passphrase")
    def has_api_passphrase_display(self, obj):
        return obj.has_api_passphrase()

    @admin.display(boolean=True, description="Broker Key")
    def has_broker_key_display(self, obj):
        return obj.has_broker_key()

    @admin.display(boolean=True, description="Trade Password")
    def has_trade_password_display(self, obj):
        return obj.has_trade_password()

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

    @admin.display(description="Spot maker fee")
    def spot_maker_fee_display(self, obj):
        return format_decimal_for_admin(obj.spot_maker_fee)

    @admin.display(description="Spot taker fee")
    def spot_taker_fee_display(self, obj):
        return format_decimal_for_admin(obj.spot_taker_fee)

    @admin.display(description="Futures maker fee")
    def futures_maker_fee_display(self, obj):
        return format_decimal_for_admin(obj.futures_maker_fee)

    @admin.display(description="Futures taker fee")
    def futures_taker_fee_display(self, obj):
        return format_decimal_for_admin(obj.futures_taker_fee)
