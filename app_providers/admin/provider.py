from django.contrib import admin

from app_providers.models import Provider


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    save_on_top = True
    empty_value_display = "—"

    list_display = (
        "provider_name",
        "code",
        "provider_type",
        "is_active",
        "priority",
        "updated_at",
    )
    list_display_links = ("provider_name",)
    list_editable = ("is_active", "priority")
    list_filter = (
        "provider_type",
        "is_active",
        "created_at",
        "updated_at",
    )
    search_fields = (
        "code",
        "affiliate_url",
        "description",
    )
    search_help_text = "Поиск по коду, партнёрской ссылке и описанию."
    readonly_fields = (
        "provider_type",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Основное",
            {
                "fields": (
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

    @admin.display(description="Провайдер")
    def provider_name(self, obj):
        return obj.get_code_display()
