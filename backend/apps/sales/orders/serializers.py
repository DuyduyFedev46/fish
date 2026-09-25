"""
Serializer đơn hàng. Đơn read-only qua API (do Hệ thống tạo, BR-PQ-11); tạo đơn đi qua
Shop API + orders.services.create_order.
"""
from rest_framework import serializers

from apps.sales.models import SalesOrder, SalesOrderLine


class SalesOrderLineSerializer(serializers.ModelSerializer):
    item_code = serializers.CharField(source="item.code", read_only=True)

    class Meta:
        model = SalesOrderLine
        fields = [
            "id", "item", "item_code", "qty", "rate", "discount_amount",
            "amount", "pricing_rule",
        ]


class SalesOrderSerializer(serializers.ModelSerializer):
    lines = SalesOrderLineSerializer(many=True, read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = SalesOrder
        fields = [
            "id", "code", "customer", "status", "status_label", "delivery_address",
            "phone", "total_amount", "booked_expires_at", "created_at", "lines",
        ]
        read_only_fields = fields  # đọc-only: đơn do Hệ thống tạo/chuyển trạng thái
