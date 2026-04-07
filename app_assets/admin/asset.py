from django.contrib import admin

from app_assets.models import Asset, AssetAlias


class AssetAliasInline(admin.TabularInline):
    model = AssetAlias
    extra = 0
    fields = (
        "code",
        "is_active",
        "created_at",
        "updated_at",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    ordering = ("code",)
    show_change_link = True


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    save_on_top = True
    empty_value_display = "—"
    inlines = (AssetAliasInline,)

    list_display = (
        "code",
        "name_short",
        "name_long",
        "asset_type",
        "is_active",
        "updated_at",
    )
    list_display_links = ("code",)
    list_editable = ("is_active",)
    list_filter = (
        "asset_type",
        "is_active",
        "updated_at",
    )
    search_fields = (
        "code",
        "name_short",
        "name_long",
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
                    "code",
                    "name_short",
                    "name_long",
                    "asset_type",
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
