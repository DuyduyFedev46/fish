"""Serializer hàng hoàn về kho — status/decision/người tạo/người duyệt chỉ đọc (BR-PQ-14/16)."""
from rest_framework import serializers

from apps.inventory.models import ReturnToStock


class ReturnToStockSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReturnToStock
        fields = [
            "id", "delivery_note", "batch", "qty", "left_warehouse_at",
            "returned_at", "decision", "status", "created_by", "approved_by", "note",
        ]
        read_only_fields = ["status", "decision", "created_by", "approved_by"]  # BR-PQ-14/16
