from django.contrib import admin

from apps.common.admin import LockedFieldsAdminMixin

from .models import (
    Customer,
    PaymentTransaction,
    Refund,
    SalesInvoice,
    SalesInvoiceLine,
    SalesInvoiceLineBatch,
    SalesOrder,
    SalesOrderLine,
    SalesOrderLineBatch,
)


class NoManualAddMixin:
    """BR-PQ-11: SalesOrder/SalesInvoice do Hệ thống tạo — không tạo tay."""

    def has_add_permission(self, request):
        return False


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("phone", "name", "created_at")
    search_fields = ("phone", "name")


class SalesOrderLineInline(admin.TabularInline):
    model = SalesOrderLine
    extra = 0
    can_delete = False
    readonly_fields = ("item", "qty", "rate", "discount_amount", "amount", "pricing_rule")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(SalesOrder)
class SalesOrderAdmin(NoManualAddMixin, LockedFieldsAdminMixin, admin.ModelAdmin):
    locked_fields = ("status", "total_amount", "customer", "booked_expires_at")
    list_display = ("code", "customer", "status", "total_amount", "booked_expires_at", "created_at")
    list_filter = ("status",)
    search_fields = ("code", "customer__phone")
    inlines = [SalesOrderLineInline]
    date_hierarchy = "created_at"


class SalesInvoiceLineInline(admin.TabularInline):
    model = SalesInvoiceLine
    extra = 0
    can_delete = False
    readonly_fields = ("item", "qty", "rate", "amount")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(SalesInvoice)
class SalesInvoiceAdmin(NoManualAddMixin, LockedFieldsAdminMixin, admin.ModelAdmin):
    locked_fields = (
        "status", "amount", "sales_order", "customer", "issued_at",
        "payment_txn_ref", "payment_method",
    )
    list_display = ("code", "sales_order", "customer", "issued_at", "amount", "status")
    list_filter = ("status", "payment_method")
    search_fields = ("code", "customer__phone", "payment_txn_ref")
    inlines = [SalesInvoiceLineInline]
    date_hierarchy = "issued_at"


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(LockedFieldsAdminMixin, admin.ModelAdmin):
    """Hàng chờ Chủ xử lý các case lệch (thiếu tiền / tới sau khi huỷ).

    S9: giao dịch do webhook ghi — người thường chỉ xem; gắn đơn/xử lý lệch đi qua console (S12).
    """

    locked_fields = (
        "bank_txn_id", "sales_order", "amount", "match_status", "source",
        "raw_payload", "received_at",
    )
    superuser_only_add = True

    list_display = ("bank_txn_id", "sales_order", "amount", "match_status", "source", "received_at")
    list_filter = ("match_status", "source")
    search_fields = ("bank_txn_id",)
    date_hierarchy = "received_at"


@admin.register(Refund)
class RefundAdmin(LockedFieldsAdminMixin, admin.ModelAdmin):
    # Phiếu hoàn chỉ sinh/chuyển trạng thái qua service (P-07, BR-HT).
    locked_fields = (
        "status", "amount", "is_partial", "sales_invoice", "bank_txn_ref",
        "confirmed_by", "confirmed_at",
    )
    actor_fields = ("created_by",)
    superuser_only_add = True
    list_display = ("id", "sales_invoice", "amount", "is_partial", "method", "status", "created_by")
    list_filter = ("status", "method", "is_partial")
    autocomplete_fields = ("sales_invoice", "created_by", "confirmed_by")
