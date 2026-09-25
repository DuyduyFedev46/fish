"""
Serializer nhà cung cấp & phiếu nhập. `PurchaseReceiptLine.rate` (đơn giá mua) nhạy cảm —
ẩn với ai không có view_costprice (spec 1.6).
"""
from rest_framework import serializers

from apps.common.api import CostFieldSerializerMixin
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
