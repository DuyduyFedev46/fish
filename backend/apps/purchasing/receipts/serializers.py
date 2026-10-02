"""
Serializer phiếu nhập (P-02) và bản ĐỌC cho màn Mua hàng (R10, 02b §3.8).

Bản đọc (`PurchaseReceiptListSerializer`, `PurchaseReceiptDetailSerializer`) khai field tường minh. Mọi tiền mua và giá vốn
(`purchase_amount`, `rate`, `landed_unit_cost`, `costs`, `allocated_amount`) nằm trong `sensitive_fields`:
chỉ người có `view_costprice` thấy (BR-MH-06, bất biến 1). Người chỉ có `view_purchasereceipt` (quản lý, nhân viên kho)
vẫn thấy mã, nhà cung cấp, mặt hàng, số kg, lô, trạng thái, hoá đơn có hay chưa. Riêng `invoices[]` (kèm `amount`) theo
quyền `purchasing.view_purchaseinvoice` (D-3): owner và manager thấy, nhân viên kho chỉ còn `invoice: {"id"}`.
"""
from decimal import ROUND_HALF_UP, Decimal

from rest_framework import serializers

from apps.catalog.models import Item
from apps.common.api import CostFieldSerializerMixin
from apps.inventory.models import Batch, Warehouse
from apps.inventory.stock.serializers import user_display_name
from apps.purchasing.models import PurchaseInvoice, PurchaseReceipt, PurchaseReceiptLine, Supplier

from .supplier_queries import attach_purchase_totals, name_taken

CENT = Decimal("0.01")
VIEW_INVOICE_PERM = "purchasing.view_purchaseinvoice"


class SupplierSerializer(CostFieldSerializerMixin, serializers.ModelSerializer):
    """
    Nhà cung cấp (B3, W5c/W5d/F1b). `receipt_count`, `last_received_at` do queryset annotate (xem
    `supplier_queries.annotate_aggregates`); `purchase_total` là tiền mua nên chỉ cho `view_costprice` (BR-MH-06).
    """

    sensitive_fields = ("purchase_total",)
    supplier_type_label = serializers.CharField(source="get_supplier_type_display", read_only=True)
    receipt_count = serializers.IntegerField(read_only=True)
    last_received_at = serializers.DateTimeField(read_only=True)
    purchase_total = serializers.SerializerMethodField()

    class Meta:
        model = Supplier
        fields = [
            "id", "name", "supplier_type", "supplier_type_label", "phone", "note", "is_active",
            "receipt_count", "last_received_at", "purchase_total",
        ]

    def validate_name(self, value):
        """Không trùng tên (không phân biệt hoa thường) với nhà cung cấp khác."""
        if name_taken(value, exclude_pk=getattr(self.instance, "pk", None)):
            raise serializers.ValidationError("Đã có nhà cung cấp trùng tên này.")
        return value

    def get_purchase_total(self, supplier):
        if not hasattr(supplier, "_purchase_total"):  # ngoài danh sách/chi tiết: tính riêng cho một nhà cung cấp
            attach_purchase_totals([supplier])
        return money(supplier._purchase_total)


class PurchaseReceiptLineSerializer(CostFieldSerializerMixin, serializers.ModelSerializer):
    sensitive_fields = ("rate",)
    item_code = serializers.CharField(source="item.code", read_only=True)

    class Meta:
        model = PurchaseReceiptLine
        fields = ["id", "receipt", "item", "item_code", "qty", "rate", "shelf_life_days", "batch"]
        read_only_fields = ["batch"]


class PurchaseReceiptSerializer(serializers.ModelSerializer):
    lines = PurchaseReceiptLineSerializer(many=True, read_only=True)

    class Meta:
        model = PurchaseReceipt
        fields = [
            "id", "supplier", "warehouse", "received_date", "status",
            "created_by", "note", "created_at", "lines",
        ]
        read_only_fields = ["status", "created_by", "created_at"]  # BR-PQ-14/16


def money(value):
    """Tiền VNĐ dạng chuỗi 2 chữ số thập phân (khớp DecimalField của API)."""
    return f"{value.quantize(CENT, rounding=ROUND_HALF_UP):.2f}"


def line_amount(line):
    """Thành tiền một dòng nhập = số kg x đơn giá mua, làm tròn đến đồng lẻ 2 chữ số."""
    return (line.qty * line.rate).quantize(CENT, rounding=ROUND_HALF_UP)


class PurchaseReceiptLineDetailSerializer(CostFieldSerializerMixin, serializers.ModelSerializer):
    """Dòng nhập kèm lô sinh ra (W2b). `rate`, `purchase_amount`, `landed_unit_cost` chỉ cho `view_costprice`."""

    sensitive_fields = ("rate", "purchase_amount", "landed_unit_cost")
    item_code = serializers.CharField(source="item.code", read_only=True)
    item_name = serializers.CharField(source="item.name", read_only=True)
    batch_code = serializers.CharField(source="batch.batch_id", read_only=True, default=None)
    batch_status = serializers.CharField(source="batch.status", read_only=True, default=None)
    expiry_date = serializers.DateField(source="batch.expiry_date", read_only=True, default=None)
    landed_unit_cost = serializers.DecimalField(
        source="batch.landed_unit_cost", max_digits=14, decimal_places=2, read_only=True, default=None
    )
    purchase_amount = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseReceiptLine
        fields = [
            "id", "item", "item_code", "item_name", "qty", "rate", "purchase_amount", "shelf_life_days",
            "batch", "batch_code", "batch_status", "expiry_date", "landed_unit_cost",
        ]
        read_only_fields = fields

    def get_purchase_amount(self, line):
        return money(line_amount(line))


class PurchaseReceiptInvoiceSerializer(serializers.ModelSerializer):
    """
    Hoá đơn mua gắn với phiếu. Có/không có hoá đơn thì ai xem phiếu cũng thấy. `amount` theo quyền xem hoá đơn mua
    (`purchasing.view_purchaseinvoice`: owner, manager), KHÔNG theo `view_costprice` (quyết định D-3, 02b §6 Q3:
    Quản lý thấy tiền hoá đơn mua). Nhân viên kho không có quyền đó nên không thấy; không có request thì ẩn.
    """

    code = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseInvoice
        fields = ["id", "code", "invoice_date", "is_paid", "amount"]
        read_only_fields = fields

    def get_code(self, invoice):
        return f"#{invoice.pk}"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        user = getattr(self.context.get("request"), "user", None)
        if not (user and user.has_perm(VIEW_INVOICE_PERM)):
            data.pop("amount", None)
        return data


class PurchaseReceiptListSerializer(CostFieldSerializerMixin, serializers.ModelSerializer):
    """Một dòng của danh sách Mua hàng (R10, W2a). Cần prefetch `lines__item`, `lines__batch`, `invoices`."""

    sensitive_fields = ("purchase_amount",)
    code = serializers.SerializerMethodField()
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    created_by_name = serializers.SerializerMethodField()
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    items_summary = serializers.SerializerMethodField()
    total_qty = serializers.SerializerMethodField()
    line_count = serializers.SerializerMethodField()
    batch_codes = serializers.SerializerMethodField()
    invoice = serializers.SerializerMethodField()
    purchase_amount = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseReceipt
        fields = [
            "id", "code", "supplier", "supplier_name", "warehouse", "warehouse_name", "received_date",
            "status", "status_label", "created_by", "created_by_name", "created_at", "note",
            "items_summary", "line_count", "total_qty", "batch_codes", "invoice", "purchase_amount",
        ]
        read_only_fields = fields

    def get_code(self, receipt):
        return f"PR-{receipt.pk}"

    def get_created_by_name(self, receipt):
        return user_display_name(receipt.created_by)

    def get_items_summary(self, receipt):
        names = []
        for line in receipt.lines.all():
            if line.item.name not in names:
                names.append(line.item.name)
        return ", ".join(names)

    def get_total_qty(self, receipt):
        return f"{sum((line.qty for line in receipt.lines.all()), Decimal('0')):.3f}"

    def get_line_count(self, receipt):
        return len(receipt.lines.all())

    def get_batch_codes(self, receipt):
        return [line.batch.batch_id for line in receipt.lines.all() if line.batch_id]

    def get_invoice(self, receipt):
        invoices = receipt.invoices.all()
        return {"id": invoices[0].pk} if invoices else None

    def get_purchase_amount(self, receipt):
        return money(sum((line_amount(line) for line in receipt.lines.all()), Decimal("0")))


class PurchaseReceiptDetailSerializer(PurchaseReceiptListSerializer):
    """
    Chi tiết phiếu nhập (R10, W2b): dòng nhập kèm lô, hoá đơn mua và chi phí phụ phân bổ vào lô của phiếu.
    `costs` và `allocated_amount` (tổng phần chi phí phụ rơi vào lô của phiếu này) chỉ cho `view_costprice`.
    Cần prefetch thêm `lines__batch__cost_allocations__purchase_cost` khi người xem có `view_costprice`.
    """

    sensitive_fields = ("purchase_amount", "costs", "allocated_amount")
    lines = PurchaseReceiptLineDetailSerializer(many=True, read_only=True)
    invoices = PurchaseReceiptInvoiceSerializer(many=True, read_only=True)
    costs = serializers.SerializerMethodField()
    allocated_amount = serializers.SerializerMethodField()

    class Meta(PurchaseReceiptListSerializer.Meta):
        fields = PurchaseReceiptListSerializer.Meta.fields + ["lines", "invoices", "costs", "allocated_amount"]
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # `invoices[]` (kèm số tiền) chỉ cho người có quyền xem hoá đơn mua; người khác còn `invoice: {"id"}` (L1).
        user = getattr(self.context.get("request"), "user", None)
        if not (user and user.has_perm(VIEW_INVOICE_PERM)):
            data.pop("invoices", None)
        return data

    def _costs(self, receipt):
        """Gom các phần phân bổ theo từng chi phí, chỉ tính phần rơi vào lô của phiếu này. Tính một lần mỗi phiếu."""
        cached = getattr(receipt, "_costs_cache", None)
        if cached is not None:
            return cached
        grouped = {}
        for line in receipt.lines.all():
            if not line.batch_id:
                continue
            for allocation in line.batch.cost_allocations.all():
                cost = allocation.purchase_cost
                entry = grouped.setdefault(cost.pk, {"cost": cost, "allocated": Decimal("0"), "batches": set()})
                entry["allocated"] += allocation.allocated_amount
                entry["batches"].add(line.batch_id)
        receipt._costs_cache = sorted(
            grouped.values(), key=lambda e: (e["cost"].incurred_date, e["cost"].pk), reverse=True
        )
        return receipt._costs_cache

    def get_costs(self, receipt):
        return [
            {
                "id": e["cost"].pk,
                "cost_type": e["cost"].cost_type,
                "cost_type_label": e["cost"].get_cost_type_display(),
                "allocation_method": e["cost"].allocation_method,
                "allocation_method_label": e["cost"].get_allocation_method_display(),
                "incurred_date": e["cost"].incurred_date.isoformat(),
                "amount": money(e["cost"].amount),
                "allocated_amount": money(e["allocated"]),
                "batch_count": len(e["batches"]),
            }
            for e in self._costs(receipt)
        ]

    def get_allocated_amount(self, receipt):
        return money(sum((e["allocated"] for e in self._costs(receipt)), Decimal("0")))


class ReceiveBatchesLine(serializers.Serializer):
    item_code = serializers.SlugRelatedField(
        slug_field="code", queryset=Item.objects.all(), help_text="Mã mặt hàng"
    )
    qty = serializers.DecimalField(
        max_digits=12, decimal_places=3, min_value=Decimal("0.001"), help_text="Số kg"
    )
    # Tối đa 10 chữ số phần nguyên: khớp Batch.landed_unit_cost (max_digits=14, decimal_places=4) — vượt thì 400 theo
    # field thay vì 500 khi ghi lô (QA Lô 10 N1).
    rate = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0.01"),  # #22: giá mua phải > 0
        help_text="Đơn giá mua/kg (> 0)"
    )
    shelf_life_days = serializers.IntegerField(
        required=False, allow_null=True, min_value=1, help_text="Hạn dùng (ngày)"
    )


class ReceiveBatchesInput(serializers.Serializer):
    supplier = serializers.PrimaryKeyRelatedField(
        queryset=Supplier.objects.filter(is_active=True), help_text="Nhà cung cấp"
    )
    received_date = serializers.DateField(required=False, help_text="Ngày nhập")
    warehouse = serializers.PrimaryKeyRelatedField(
        queryset=Warehouse.objects.all(), required=False, help_text="Kho nhập"
    )
    idempotency_key = serializers.CharField(
        max_length=64, required=False, allow_blank=True, allow_null=True, help_text="Khoá lặp"
    )
    lines = ReceiveBatchesLine(many=True, min_length=1)


class ReceivedBatchOutput(CostFieldSerializerMixin, serializers.ModelSerializer):
    sensitive_fields = ("purchase_rate", "landed_unit_cost")

    class Meta:
        model = Batch
        fields = [
            "batch_id", "status", "expiry_date", "qty_available", "purchase_rate", "landed_unit_cost"
        ]
