from django.contrib import admin

from app_assets.models import AssetAlias


@admin.register(AssetAlias)
class AssetAliasAdmin(admin.ModelAdmin):
    save_on_top = True
    empty_value_display = "—"
    list_select_related = ("asset",)

    list_display = (
        "code",
        "asset",
        "is_active",
        "updated_at",
    )
    list_display_links = ("code",)
    list_editable = ("is_active",)
    list_filter = (
        "is_active",
        "updated_at",
    )
    search_fields = (
        "code",
        "asset__code",
        "asset__name_short",
        "asset__name_long",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )
    ordering = ("code",)
    list_per_page = 50

    fieldsets = (
        (
            "Основное",
            {
                "fields": (
                    "id",
                    "asset",
                    "code",
                    "is_active",
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
