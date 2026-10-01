"""Serializer khách hàng."""
from rest_framework import serializers

from apps.sales.models import Customer


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["id", "phone", "name", "default_address", "note", "created_at"]
        read_only_fields = ["created_at"]


class CourierCustomerSerializer(serializers.ModelSerializer):
    """NV giao (SR-PII-02 AC4): chỉ thông tin cần để giao; không `note` nội bộ, không `default_address`
    (địa chỉ giao của chính đơn đã có ở chi tiết đơn). Read-only: nv_giao cũng không có quyền ghi."""

    class Meta:
        model = Customer
        fields = ["id", "phone", "name", "created_at"]
        read_only_fields = fields
