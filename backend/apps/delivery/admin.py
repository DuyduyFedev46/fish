from django.contrib import admin

from apps.common.admin import LockedFieldsAdminMixin

from .models import DeliveryNote


@admin.register(DeliveryNote)
class DeliveryNoteAdmin(LockedFieldsAdminMixin, admin.ModelAdmin):
    # S9 = danh sách khoá API của S3. Phiếu giao do hệ thống sinh khi có hoá đơn.
    locked_fields = ("status", "assigned_to", "failed_attempts", "completed_at", "sales_invoice")
    superuser_only_add = True
    list_display = ("code", "sales_invoice", "status", "assigned_to", "failed_attempts", "created_at")
    list_filter = ("status",)
    search_fields = ("code", "sales_invoice__code")
    autocomplete_fields = ("sales_invoice", "assigned_to")
    date_hierarchy = "created_at"
