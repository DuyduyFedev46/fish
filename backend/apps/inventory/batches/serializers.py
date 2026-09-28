"""
Serializer lô. `BatchSerializer` ẩn field giá vốn (purchase_rate, landed_unit_cost)
với ai không có `inventory.view_costprice` — Tầng 3 phạm vi cột (spec 1.6).
"""
from rest_framework import serializers

from apps.catalog.models import Item
from apps.common.api import CostFieldSerializerMixin
from apps.inventory.models import Batch


class BatchSerializer(CostFieldSerializerMixin, serializers.ModelSerializer):
    sensitive_fields = ("purchase_rate", "landed_unit_cost")
    item_code = serializers.CharField(source="item.code", read_only=True)
    qty_sellable = serializers.DecimalField(max_digits=12, decimal_places=3, read_only=True)

    class Meta:
        model = Batch
        fields = [
            "id", "batch_id", "item", "item_code", "supplier", "warehouse",
            "received_date", "expiry_date", "qty_received", "qty_available",
            "qty_reserved", "qty_sellable", "status", "closed_at",
            "purchase_rate", "landed_unit_cost",  # nhạy cảm — mixin loại nếu thiếu quyền
        ]
        read_only_fields = ["batch_id", "qty_available", "qty_reserved", "closed_at"]


class BatchListQuery(serializers.Serializer):
    """Tham số lọc danh sách lô (02b §2.5, DW-07-AC10)."""
    item_code = serializers.SlugRelatedField(
        slug_field="code", queryset=Item.objects.all(), required=False, help_text="Mã mặt hàng"
    )
    status = serializers.ChoiceField(choices=Batch.Status.choices, required=False)
