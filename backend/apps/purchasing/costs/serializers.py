"""Serializer chi phí mua + phân bổ lô — toàn bộ là dữ liệu giá vốn (chỉ Chủ)."""
from rest_framework import serializers

from apps.purchasing.models import PurchaseCost, PurchaseCostAllocation


class PurchaseCostAllocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseCostAllocation
        fields = ["id", "purchase_cost", "batch", "allocated_amount"]


class PurchaseCostSerializer(serializers.ModelSerializer):
    """Toàn bộ chứng từ chi phí là nhạy cảm — chỉ Chủ (add_purchasecost/view_costprice)."""

    allocations = PurchaseCostAllocationSerializer(many=True, read_only=True)

    class Meta:
        model = PurchaseCost
        fields = [
            "id", "cost_type", "amount", "allocation_method", "incurred_date",
            "note", "created_by", "created_at", "allocations",
        ]
        read_only_fields = ["created_by", "created_at"]  # BR-PQ-16
