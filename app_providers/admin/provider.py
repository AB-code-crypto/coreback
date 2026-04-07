from django.contrib import admin

from app_providers.models.provider import Provider


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "is_active",
        "priority",
        "provider_type",
        "updated_at",
    )
    list_display_links = ("name",)
    list_editable = ("is_active", "priority")
    list_filter = ("provider_type", "is_active", "updated_at")
    search_fields = ("name", "code", "description")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-is_active", "priority", "name")
    list_per_page = 50

    fieldsets = (
        (
            "Основное",
            {
                "fields": (
                    "name",
                    "code",
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
                    "metadata",
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
