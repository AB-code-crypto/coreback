from django import forms
from django.contrib import admin

from app_core.models.platform_fee import PlatformFee
from app_core.utils.decimal_format import format_decimal_for_admin


class PlatformFeeAdminForm(forms.ModelForm):
    class Meta:
        model = PlatformFee
        fields = (
            "min_amount",
            "max_amount",
            "fee_percent",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value = getattr(self.instance, "fee_percent", None)
        if value is not None:
            self.initial["fee_percent"] = format_decimal_for_admin(value)


@admin.register(PlatformFee)
class PlatformFeeAdmin(admin.ModelAdmin):
    form = PlatformFeeAdminForm

    save_on_top = True
    empty_value_display = "—"

    list_display = (
        "id",
        "min_amount",
        "max_amount",
        "fee_percent",
        "updated_at",
    )
    list_display_links = ("id",)
    list_editable = (
        "min_amount",
        "max_amount",
        "fee_percent",
    )

    ordering = ("min_amount",)
    list_per_page = 50
    readonly_fields = (
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Диапазон суммы",
            {
                "fields": (
                    "min_amount",
                    "max_amount",
                ),
                "description": (
                    "Диапазоны должны быть непрерывными, без пересечений и без дыр. "
                    "Нижняя граница включается, верхняя — не включается. "
                    "Первый диапазон должен начинаться с 0."
                ),
            },
        ),
        (
            "Комиссия платформы",
            {
                "fields": ("fee_percent",),
                "description": (
                    "Комиссия указывается в процентах. "
                    "Например: 1.5 = 1.5%, 0.75 = 0.75%."
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
