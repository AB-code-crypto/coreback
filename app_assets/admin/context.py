from django.contrib import admin

from app_assets.models import Context


@admin.register(Context)
class ContextAdmin(admin.ModelAdmin):
    save_on_top = True
    empty_value_display = "—"

    list_display = (
        "code",
        "name_short",
        "name_long",
        "context_type",
        "is_active",
        "updated_at",
    )
    list_display_links = ("code",)
    list_editable = ("is_active",)
    list_filter = (
        "context_type",
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
    ordering = ("context_type", "code")
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
                    "context_type",
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
