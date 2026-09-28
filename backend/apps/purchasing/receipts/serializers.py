from decimal import Decimal
from rest_framework import serializers

from apps.catalog.models import Item
from apps.common.api import CostFieldSerializerMixin
from apps.inventory.models import Batch, Warehouse
from apps.purchasing.models import PurchaseReceipt, PurchaseReceiptLine, Supplier


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ["id", "name", "supplier_type", "phone", "note", "is_active"]


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


class NhapLoLine(serializers.Serializer):
    item_code = serializers.SlugRelatedField(
        slug_field="code", queryset=Item.objects.all(), help_text="Mã mặt hàng"
    )
    qty = serializers.DecimalField(
        max_digits=12, decimal_places=3, min_value=Decimal("0.001"), help_text="Số kg"
    )
    rate = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal("0"), help_text="Đơn giá mua/kg"
    )
    shelf_life_days = serializers.IntegerField(
        required=False, allow_null=True, min_value=1, help_text="Hạn dùng (ngày)"
    )


class NhapLoInput(serializers.Serializer):
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
    lines = NhapLoLine(many=True, min_length=1)


class NhapLoBatchOutput(CostFieldSerializerMixin, serializers.ModelSerializer):
    sensitive_fields = ("purchase_rate", "landed_unit_cost")

    class Meta:
        model = Batch
        fields = [
            "batch_id", "status", "expiry_date", "qty_available", "purchase_rate", "landed_unit_cost"
        ]
