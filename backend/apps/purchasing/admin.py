from django.contrib import admin

from apps.common.admin import LockedFieldsAdminMixin
from apps.inventory.admin import CostHidingMixin

from .models import (
    PurchaseCost,
    PurchaseCostAllocation,
    PurchaseInvoice,
    PurchaseReceipt,
    PurchaseReceiptLine,
    Supplier,
)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "supplier_type", "phone", "is_active")
    list_filter = ("supplier_type", "is_active")
    search_fields = ("name", "phone")


class PurchaseReceiptLineInline(CostHidingMixin, admin.TabularInline):
    """
    `rate` (giá mua) chỉ hiện với người có `inventory.view_costprice` (§1.6, BR-MH-06).
    Người thiếu quyền không thêm dòng ở Admin: `rate` bắt buộc mà họ không được thấy/nhập —
    nhập hàng đi qua API phiếu nhập.
    """

    model = PurchaseReceiptLine
    cost_fields = ("rate",)
    extra = 1
    autocomplete_fields = ("item", "batch")

    def has_add_permission(self, request, obj=None):
        return self._can_see_cost(request) and super().has_add_permission(request, obj)


@admin.register(PurchaseReceipt)
class PurchaseReceiptAdmin(LockedFieldsAdminMixin, admin.ModelAdmin):
    locked_fields = ("status",)
    actor_fields = ("created_by",)
    list_display = ("id", "supplier", "warehouse", "received_date", "status", "created_by")
    list_filter = ("status", "warehouse")
    search_fields = ("supplier__name",)
    autocomplete_fields = ("supplier", "warehouse", "created_by")
    inlines = [PurchaseReceiptLineInline]
    date_hierarchy = "received_date"


@admin.register(PurchaseInvoice)
class PurchaseInvoiceAdmin(admin.ModelAdmin):
    list_display = ("id", "supplier", "amount", "is_paid", "invoice_date")
    list_filter = ("is_paid",)
    autocomplete_fields = ("supplier", "receipt", "created_by")
    date_hierarchy = "invoice_date"


class PurchaseCostAllocationInline(admin.TabularInline):
    model = PurchaseCostAllocation
    extra = 1
    autocomplete_fields = ("batch",)


@admin.register(PurchaseCost)
class PurchaseCostAdmin(admin.ModelAdmin):
    """Chỉ Chủ có builtin `add_purchasecost` — đụng thẳng giá vốn (P-03)."""

    list_display = ("id", "cost_type", "amount", "allocation_method", "incurred_date")
    list_filter = ("cost_type", "allocation_method")
    autocomplete_fields = ("created_by",)
    inlines = [PurchaseCostAllocationInline]
    date_hierarchy = "incurred_date"
