"""Serializer phiếu hoàn tiền — status/người tạo/người xác nhận chỉ đọc (BR-PQ-14/16).

S13: thêm `payment_transaction` (phiếu hoàn không hoá đơn, `sales_invoice` = null) và
`request_id` (Q12). `amount` là chuỗi tiền theo quy ước contract ("300000", không ".00").
"""
from rest_framework import serializers

from apps.sales.models import Refund
from apps.sales.utils import money_str


class RefundSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    amount = serializers.SerializerMethodField()

    class Meta:
        model = Refund
        fields = [
            "id", "sales_invoice", "payment_transaction", "amount", "is_partial", "method",
            "status", "status_label", "bank_txn_ref", "reason", "created_by", "confirmed_by",
            "created_at", "confirmed_at", "request_id",
        ]
        read_only_fields = fields  # chỉ sinh / chuyển trạng thái qua service (BR-PQ-14/16)

    def get_amount(self, obj):
        return money_str(obj.amount)
