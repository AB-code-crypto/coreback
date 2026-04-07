from django.contrib import admin

from app_tenancy.models.tenant import Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    save_on_top = True
    empty_value_display = "—"

    list_display = (
        "code",
        "is_active",
        "license_type",
        "license_until",
        "allowed_ip_ranges",
        "created_at",
        "updated_at",
    )
    list_display_links = ("code",)
    list_filter = (
        "is_active",
        "license_type",
        "license_until",
        "created_at",
        "updated_at",
    )
    search_fields = (
        "code",
        "description",
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
                    "is_active",
                ),
            },
        ),
        (
            "Лицензия",
            {
                "fields": (
                    "license_type",
                    "license_until",
                ),
                "description": (
                    "Тип лицензии tenant-а и срок её действия. "
                    "Для демо-доступа и аренды срок обычно указывается, "
                    "для купленной лицензии может быть пустым."
                ),
            },
        ),
        (
            "Доступ по IP",
            {
                "fields": ("allowed_ip_ranges",),
                "description": (
                    "Список разрешённых IP или CIDR. "
                    "Если список пуст, доступ tenant-у запрещён."
                ),
            },
        ),
        (
            "Дополнительно",
            {
                "fields": (
                    "description",
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )
