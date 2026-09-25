from django.contrib import admin

from apps.common.admin import LockedFieldsAdminMixin

from .models import (
    Batch,
    ReturnToStock,
    StockEntry,
    StockLedgerEntry,
    StockReconciliation,
    StockReconciliationLine,
    Warehouse,
)


class CostHidingMixin:
    """
    Tầng 3 — phạm vi CỘT (1.6). Ẩn field giá vốn khỏi người không có
    `inventory.view_costprice`. Ở Admin việc ẩn dễ; cảnh báo của spec là DRF
    (Phase 3) phải tách serializer, không dùng chung fields='__all__'.
    """

    cost_fields: tuple = ()

    def _can_see_cost(self, request):
        return request.user.has_perm("inventory.view_costprice")

    def get_exclude(self, request, obj=None):
        base = list(super().get_exclude(request, obj) or [])
        if not self._can_see_cost(request):
            base += [f for f in self.cost_fields if f not in base]
        return base

    def get_readonly_fields(self, request, obj=None):
        # Field giá vốn bị khoá chỉ đọc (S9) vẫn phải ẩn với người không xem giá vốn.
        readonly = list(super().get_readonly_fields(request, obj))
        if not self._can_see_cost(request):
            readonly = [f for f in readonly if f not in self.cost_fields]
        return readonly

    def get_list_display(self, request):
        ld = list(super().get_list_display(request))
        if not self._can_see_cost(request):
            ld = [f for f in ld if f not in self.cost_fields]
        return ld


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("name", "is_group")
    search_fields = ("name",)


@admin.register(Batch)
class BatchAdmin(CostHidingMixin, LockedFieldsAdminMixin, admin.ModelAdmin):
    cost_fields = ("purchase_rate", "landed_unit_cost")
    # S9 = danh sách khoá API của S3 (BR-PQ-14). Lô chỉ sinh từ phiếu nhập.
    locked_fields = (
        "status", "qty_received", "qty_available", "qty_reserved", "purchase_rate",
        "landed_unit_cost", "expiry_date", "closed_at", "closed_by",
    )
    superuser_only_add = True
    list_display = (
        "batch_id", "item", "supplier", "status", "received_date", "expiry_date",
        "qty_received", "qty_available", "qty_reserved", "landed_unit_cost",
    )
    list_filter = ("status", "warehouse", "supplier")
    search_fields = ("batch_id", "item__code", "item__name")
    autocomplete_fields = ("item", "supplier", "warehouse", "closed_by")
    date_hierarchy = "received_date"


class StockReconciliationLineInline(admin.TabularInline):
    model = StockReconciliationLine
    extra = 1
    autocomplete_fields = ("batch",)


@admin.register(StockReconciliation)
class StockReconciliationAdmin(LockedFieldsAdminMixin, admin.ModelAdmin):
    locked_fields = ("status", "approved_by", "approved_at")
    actor_fields = ("created_by",)
    list_display = ("id", "count_date", "status", "created_by", "approved_by")
    list_filter = ("status",)
    autocomplete_fields = ("created_by", "approved_by")
    inlines = [StockReconciliationLineInline]
    date_hierarchy = "count_date"


@admin.register(ReturnToStock)
class ReturnToStockAdmin(LockedFieldsAdminMixin, admin.ModelAdmin):
    locked_fields = ("status", "decision", "approved_by")
    actor_fields = ("created_by",)
    list_display = ("id", "batch", "qty", "decision", "status", "created_by", "approved_by")
    list_filter = ("decision", "status")
    autocomplete_fields = ("batch", "delivery_note", "created_by", "approved_by")


@admin.register(StockEntry)
class StockEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "purpose", "batch", "qty_change", "created_by", "created_at")
    list_filter = ("purpose",)
    autocomplete_fields = ("batch", "created_by")


@admin.register(StockLedgerEntry)
class StockLedgerEntryAdmin(admin.ModelAdmin):
    """Sổ chuyển động — chỉ đọc (system-written)."""

    list_display = ("created_at", "batch", "movement_type", "qty_change", "reference")
    list_filter = ("movement_type",)
    search_fields = ("batch__batch_id", "reference")
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
