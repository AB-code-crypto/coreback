from django.contrib import admin

from app_assets.models import AssetContext


@admin.register(AssetContext)
class AssetContextAdmin(admin.ModelAdmin):
    save_on_top = True
    empty_value_display = "—"
    list_select_related = ("asset", "context")

    list_display = (
        "code",
        "asset",
        "context",
        "name_short_display",
        "is_active",
        "updated_at",
    )
    list_display_links = ("code",)
    list_editable = ("is_active",)
    list_filter = (
        "asset__asset_type",
        "context__context_type",
        "is_active",
        "updated_at",
    )
    search_fields = (
        "code",
        "asset__code",
        "asset__name_short",
        "asset__name_long",
        "context__code",
        "context__name_short",
        "context__name_long",
    )

    readonly_fields = (
        "id",
        "code",
        "name_short_display",
        "name_long_display",
        "created_at",
        "updated_at",
    )
    ordering = ("asset__code", "context__code")
    list_per_page = 50

    fieldsets = (
        (
            "Основное",
            {
                "fields": (
                    "id",
                    "asset",
                    "context",
                    "code",
                    "is_active",
                )
            },
        ),
        (
            "Отображение",
            {
                "fields": (
                    "name_short_display",
                    "name_long_display",
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

    @admin.display(description="Короткое название")
    def name_short_display(self, obj):
        return obj.name_short

    @admin.display(description="Полное название")
    def name_long_display(self, obj):
        return obj.name_long
