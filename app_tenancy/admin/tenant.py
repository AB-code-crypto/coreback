from django.contrib import admin

from app_tenancy.models import Tenant, TenantStatus, TenantAccessPolicy


class TenantStatusInline(admin.StackedInline):
    model = TenantStatus
    extra = 0
    max_num = 1
    can_delete = False


class TenantAccessPolicyInline(admin.StackedInline):
    model = TenantAccessPolicy
    extra = 0
    max_num = 1
    can_delete = False


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "is_active",
        "created_at",
        "updated_at",
    )
    search_fields = (
        "code",
        "name",
    )
    list_filter = (
        "is_active",
        "created_at",
        "updated_at",
    )
    ordering = ("name",)
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )
    inlines = (
        TenantStatusInline,
        TenantAccessPolicyInline,
    )
    fieldsets = (
        (
            "Основное",
            {
                "fields": (
                    "id",
                    "code",
                    "name",
                    "is_active",
                    "notes",
                )
            },
        ),
        (
            "Служебное",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


@admin.register(TenantStatus)
class TenantStatusAdmin(admin.ModelAdmin):
    list_display = (
        "tenant",
        "status",
        "updated_at",
    )
    search_fields = (
        "tenant__code",
        "tenant__name",
        "reason",
    )
    list_filter = (
        "status",
        "updated_at",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )


@admin.register(TenantAccessPolicy)
class TenantAccessPolicyAdmin(admin.ModelAdmin):
    list_display = (
        "tenant",
        "is_ip_whitelist_enabled",
        "updated_at",
    )
    search_fields = (
        "tenant__code",
        "tenant__name",
        "policy_notes",
    )
    list_filter = (
        "is_ip_whitelist_enabled",
        "updated_at",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
