from django.contrib import admin

from app_providers.forms import ProviderAdminForm
from app_providers.models.provider import Provider


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    form = ProviderAdminForm
    save_on_top = True
    empty_value_display = "—"

    list_display = (
        "name",
        "code",
        "is_active",
        "priority",
        "provider_type",
        "updated_at",
    )
    list_display_links = ("name",)
    list_editable = ("is_active", "priority")
    list_filter = ("provider_type", "is_active", "updated_at")
    search_fields = ("name", "code", "description")
    search_help_text = "Поиск по названию, коду и описанию провайдера."
    readonly_fields = (
        "name",
        "provider_type",
        "affiliate_url",
        "created_at",
        "updated_at",
    )
    ordering = ("-is_active", "priority", "name")
    list_per_page = 50

    fieldsets = (
        (
            "Основное",
            {
                "fields": (
                    "code",
                    "name",
                    "provider_type",
                    "is_active",
                    "priority",
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
