from django import forms
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import reverse

from app_core.models.platform_settings import PlatformSettings


class PlatformSettingsAdminForm(forms.ModelForm):
    class Meta:
        model = PlatformSettings
        fields = (
            "stablecoin_codes",
            "fiat_currency_codes",
            "memo_tag_network_codes",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["stablecoin_codes"].widget = forms.Textarea(
            attrs={"rows": 4, "style": "width: 100%;"}
        )
        self.fields["fiat_currency_codes"].widget = forms.Textarea(
            attrs={"rows": 6, "style": "width: 100%;"}
        )
        self.fields["memo_tag_network_codes"].widget = forms.Textarea(
            attrs={"rows": 3, "style": "width: 100%;"}
        )

        self.initial["stablecoin_codes"] = self._to_comma_separated(
            self.instance.stablecoin_codes
        )
        self.initial["fiat_currency_codes"] = self._to_comma_separated(
            self.instance.fiat_currency_codes
        )
        self.initial["memo_tag_network_codes"] = self._to_comma_separated(
            self.instance.memo_tag_network_codes
        )

    @staticmethod
    def _to_comma_separated(value: str) -> str:
        if not value:
            return ""

        items = [item.strip() for item in value.splitlines() if item.strip()]
        return ", ".join(items)


@admin.register(PlatformSettings)
class PlatformSettingsAdmin(admin.ModelAdmin):
    form = PlatformSettingsAdminForm

    save_on_top = True
    empty_value_display = "—"

    list_display = (
        "id",
        "stablecoin_count",
        "fiat_count",
        "memo_tag_network_count",
        "updated_at",
    )
    readonly_fields = ("created_at", "updated_at")
    search_fields = ()
    list_per_page = 50

    fieldsets = (
        (
            "Глобальные списки",
            {
                "fields": (
                    "stablecoin_codes",
                    "fiat_currency_codes",
                    "memo_tag_network_codes",
                ),
                "description": (
                    "Списки можно вводить в одну строку через запятую. "
                    "При сохранении значения будут очищены от дублей и отсортированы."
                ),
            },
        ),
        (
            "Технические работы",
            {
                "fields": (
                    "maintenance_mode_enabled",
                    "maintenance_reason",
                ),
                "description": (
                    "Если режим включён, downstream-сервисы смогут понять, что ядро "
                    "временно недоступно или работает в ограниченном режиме."
                ),
            },
        ),
        (
            "Telegram",
            {
                "fields": (
                    "telegram_notifications_enabled",
                    "telegram_bot_token",
                    "telegram_channel_id",
                ),
                "description": (
                    "Настройки отправки уведомлений о событиях ядра в Telegram."
                ),
            },
        ),
        (
            "Служебная информация",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )

    def has_add_permission(self, request):
        if PlatformSettings.objects.exists():
            return False
        return super().has_add_permission(request)

    def changelist_view(self, request, extra_context=None):
        obj = PlatformSettings.objects.first()
        if obj:
            url = reverse("admin:app_core_platformsettings_change", args=[obj.pk])
            return HttpResponseRedirect(url)
        return super().changelist_view(request, extra_context=extra_context)

    @admin.display(description="Стейблкоины")
    def stablecoin_count(self, obj):
        return len(obj.get_stablecoin_codes())

    @admin.display(description="Фиаты")
    def fiat_count(self, obj):
        return len(obj.get_fiat_currency_codes())

    @admin.display(description="Сети с MEMO/TAG")
    def memo_tag_network_count(self, obj):
        return len(obj.get_memo_tag_network_codes())
