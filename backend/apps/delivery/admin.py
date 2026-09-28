from django.contrib import admin

from apps.common.admin import LockedFieldsAdminMixin

from .models import ConfirmationTask, CustomerCall, DeliveryNote, LabelPrint


@admin.register(DeliveryNote)
class DeliveryNoteAdmin(LockedFieldsAdminMixin, admin.ModelAdmin):
    # S9 = danh sách khoá API của S3 + CSKH. Phiếu giao do hệ thống sinh khi có hoá đơn.
    locked_fields = (
        "status", "assigned_to", "failed_attempts", "completed_at", "sales_invoice",
        "confirmed_at", "confirmed_by", "confirm_skipped",
    )
    exclude = ("recipient_name", "recipient_phone")
    superuser_only_add = True
    list_display = ("code", "sales_invoice", "status", "assigned_to", "failed_attempts", "created_at")
    list_filter = ("status",)
    search_fields = ("code", "sales_invoice__code")
    autocomplete_fields = ("sales_invoice", "assigned_to")
    date_hierarchy = "created_at"


@admin.register(ConfirmationTask)
class ConfirmationTaskAdmin(admin.ModelAdmin):
    list_display = ("id", "note", "state", "escalation_reason", "attempts", "escalated_at")
    list_filter = ("state", "escalation_reason")
    search_fields = ("note__code",)
    readonly_fields = [f.name for f in ConfirmationTask._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CustomerCall)
class CustomerCallAdmin(admin.ModelAdmin):
    list_display = ("id", "note", "result", "created_by", "created_at")
    list_filter = ("result",)
    search_fields = ("note__code",)
    readonly_fields = [f.name for f in CustomerCall._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LabelPrint)
class LabelPrintAdmin(admin.ModelAdmin):
    list_display = ("id", "note", "print_no", "reason", "printed_by", "printed_at")
    list_filter = ("reason",)
    search_fields = ("note__code",)
    readonly_fields = [f.name for f in LabelPrint._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
