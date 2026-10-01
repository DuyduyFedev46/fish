"""
Serializer chi phí mua + phân bổ lô — toàn bộ là dữ liệu giá vốn (landed cost): chỉ Chủ có `view_purchasecost` và
`view_costprice` (api.py chặn 403 trước khi tới đây). Không có field nào để ẩn từng phần, nên người không đủ quyền không
nhận được thân phản hồi nào.
"""
from rest_framework import serializers

from apps.purchasing.models import PurchaseCost, PurchaseCostAllocation


class PurchaseCostAllocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseCostAllocation
        fields = ["id", "purchase_cost", "batch", "allocated_amount"]


class PurchaseCostSerializer(serializers.ModelSerializer):
    """`batch_count` = số lô nhận phân bổ (đếm trên `allocations` đã prefetch, không thêm truy vấn)."""

    allocations = PurchaseCostAllocationSerializer(many=True, read_only=True)
    cost_type_label = serializers.CharField(source="get_cost_type_display", read_only=True)
    allocation_method_label = serializers.CharField(source="get_allocation_method_display", read_only=True)
    batch_count = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseCost
        fields = [
            "id", "cost_type", "cost_type_label", "amount", "allocation_method", "allocation_method_label",
            "incurred_date", "note", "created_by", "created_at", "allocations", "batch_count",
        ]
        read_only_fields = ["created_by", "created_at"]  # BR-PQ-16

    def get_batch_count(self, cost):
        return len(cost.allocations.all())
