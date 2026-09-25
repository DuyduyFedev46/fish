"""Serializer phiếu kiểm kê + dòng kiểm kê theo lô."""
from rest_framework import serializers

from apps.inventory.models import StockReconciliation, StockReconciliationLine


class StockReconciliationLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockReconciliationLine
        fields = ["id", "batch", "system_qty", "counted_qty", "difference_qty", "reason"]
        read_only_fields = ["difference_qty"]


class StockReconciliationSerializer(serializers.ModelSerializer):
    lines = StockReconciliationLineSerializer(many=True, read_only=True)

    class Meta:
        model = StockReconciliation
        fields = [
            "id", "count_date", "status", "created_by", "approved_by",
            "approved_at", "note", "lines",
        ]
        read_only_fields = ["status", "created_by", "approved_by", "approved_at"]  # BR-PQ-14/16
