"""
Serializer hoá đơn bán & giao dịch thanh toán. `unit_cost` trên SalesInvoiceLineBatch là
nhạy cảm (giá vốn) — ẩn với ai không có view_costprice (spec 1.6). Read-only (BR-PQ-11).
"""
from rest_framework import serializers

from apps.common.api import CostFieldSerializerMixin
from apps.sales.models import (
    PaymentTransaction,
    SalesInvoice,
    SalesInvoiceLine,
    SalesInvoiceLineBatch,
)


class SalesInvoiceLineBatchSerializer(CostFieldSerializerMixin, serializers.ModelSerializer):
    sensitive_fields = ("unit_cost",)

    class Meta:
        model = SalesInvoiceLineBatch
        fields = ["id", "invoice_line", "batch", "component_item", "qty", "unit_cost"]


class SalesInvoiceLineSerializer(serializers.ModelSerializer):
    batch_allocations = SalesInvoiceLineBatchSerializer(many=True, read_only=True)
    item_code = serializers.CharField(source="item.code", read_only=True)

    class Meta:
        model = SalesInvoiceLine
        fields = ["id", "item", "item_code", "qty", "rate", "amount", "batch_allocations"]


class SalesInvoiceSerializer(serializers.ModelSerializer):
    lines = SalesInvoiceLineSerializer(many=True, read_only=True)

    class Meta:
        model = SalesInvoice
        fields = [
            "id", "code", "sales_order", "customer", "issued_at", "amount",
            "payment_txn_ref", "payment_method", "status", "lines",
        ]
        read_only_fields = fields


class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = [
            "id", "bank_txn_id", "sales_order", "amount", "match_status",
            "source", "received_at", "created_at",
        ]
        read_only_fields = fields
