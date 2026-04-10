from django.contrib import admin

from app_providers.models import RawData


@admin.register(RawData)
class RawDataAdmin(admin.ModelAdmin):
    save_on_top = True
    empty_value_display = "—"
    list_select_related = ("provider",)

    list_display = (
        "id",
        "provider",
        "request_type",
        "request_status",
        "http_status",
        "is_processed",
        "requested_at",
        "responded_at",
        "created_at",
    )
    list_display_links = ("id",)
    list_filter = (
        "provider",
        "request_type",
        "request_status",
        "is_processed",
        "created_at",
        "requested_at",
        "responded_at",
    )
    search_fields = (
        "provider__code",
        "source",
        "file_path",
        "processing_error",
    )
    search_help_text = "Поиск по провайдеру, источнику, пути к файлу и ошибке обработки."
    ordering = ("-created_at",)
    list_per_page = 50

    readonly_fields = (
        "id",
        "provider",
        "request_type",
        "request_status",
        "source",
        "http_status",
        "file_path",
        "is_processed",
        "processing_error",
        "requested_at",
        "responded_at",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Основное",
            {
                "fields": (
                    "id",
                    "provider",
                    "request_type",
                    "request_status",
                    "source",
                    "http_status",
                )
            },
        ),
        (
            "Файл и обработка",
            {
                "fields": (
                    "file_path",
                    "is_processed",
                    "processing_error",
                )
            },
        ),
        (
            "Время",
            {
                "fields": (
                    "requested_at",
                    "responded_at",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
