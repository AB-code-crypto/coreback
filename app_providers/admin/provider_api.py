from django import forms
from django.contrib import admin

from app_providers.models.provider_api import ProviderApi


class ProviderApiAdminForm(forms.ModelForm):
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
        model = ProviderApi
        fields = (
            "provider",
            "name",
            "is_active",
            "priority",
            "spot_maker_fee",
            "spot_taker_fee",
            "futures_maker_fee",
            "futures_taker_fee",
            "is_ip_whitelist_enabled",
            "allowed_ip_ranges",
            "description",
        )

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


@admin.register(ProviderApi)
class ProviderApiAdmin(admin.ModelAdmin):
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
