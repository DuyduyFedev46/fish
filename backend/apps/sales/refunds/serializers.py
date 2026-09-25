"""Serializer phiếu hoàn tiền — status/người tạo/người xác nhận chỉ đọc (BR-PQ-14/16).

S13: thêm `payment_transaction` (phiếu hoàn không hoá đơn, `sales_invoice` = null) và
`request_id` (Q12). `amount` là chuỗi tiền theo quy ước contract ("300000", không ".00").
S16: thêm dữ liệu để dựng màn "Phiếu hoàn chờ chuyển" — `order_code`/`customer_*` (từ hoá
đơn hoặc giao dịch gắn), `source_bank_txn_id` (mã GD gốc để đối chiếu), `failure_reason`
(BR-HT-09) và `available_actions` (luật + quyền, chỉ Chủ có `confirm_refund`).
"""
from rest_framework import serializers

from apps.sales.models import Refund
from apps.sales.utils import money_str


class RefundSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    amount = serializers.SerializerMethodField()
    order_code = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    customer_phone = serializers.SerializerMethodField()
    source_bank_txn_id = serializers.SerializerMethodField()
    available_actions = serializers.SerializerMethodField()

    class Meta:
        model = Refund
        fields = [
            "id", "sales_invoice", "payment_transaction", "amount", "is_partial", "method",
            "status", "status_label", "bank_txn_ref", "reason", "created_by", "confirmed_by",
            "created_at", "confirmed_at", "request_id",
            "order_code", "customer_name", "customer_phone", "source_bank_txn_id",
            "failure_reason", "available_actions",
        ]
        read_only_fields = fields  # chỉ sinh / chuyển trạng thái qua service (BR-PQ-14/16)

    def get_amount(self, obj):
        return money_str(obj.amount)

    def _order(self, obj):
        if obj.sales_invoice_id:
            return obj.sales_invoice.sales_order
        if obj.payment_transaction_id:
            return obj.payment_transaction.sales_order
        return None

    def get_order_code(self, obj):
        order = self._order(obj)
        return order.code if order else None

    def get_customer_name(self, obj):
        order = self._order(obj)
        return order.customer.name if order else ""

    def get_customer_phone(self, obj):
        order = self._order(obj)
        return order.phone if order else ""

    def get_source_bank_txn_id(self, obj):
        if obj.payment_transaction_id:
            return obj.payment_transaction.bank_txn_id
        if obj.sales_invoice_id:
            return obj.sales_invoice.payment_txn_ref
        return ""

    def get_available_actions(self, obj):
        from .services import refund_available_actions

        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user is None:
            return []
        return refund_available_actions(refund=obj, user=user)
