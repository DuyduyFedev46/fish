"""Serializer phiếu hoàn tiền — status/người tạo/người xác nhận chỉ đọc (BR-PQ-14/16)."""
from rest_framework import serializers

from apps.sales.models import Refund


class RefundSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Refund
        fields = [
            "id", "sales_invoice", "amount", "is_partial", "method", "status",
            "status_label", "bank_txn_ref", "reason", "created_by", "confirmed_by",
            "created_at", "confirmed_at",
        ]
        read_only_fields = [
            "status", "created_by", "confirmed_by", "confirmed_at", "created_at",
        ]  # BR-PQ-14/16
