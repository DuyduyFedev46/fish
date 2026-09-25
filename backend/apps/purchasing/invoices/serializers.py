"""Serializer hoá đơn mua (số tiền là dữ liệu chi phí — quyền xem theo Group, BR-PQ)."""
from rest_framework import serializers

from apps.purchasing.models import PurchaseInvoice


class PurchaseInvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseInvoice
        fields = [
            "id", "supplier", "receipt", "amount", "is_paid",
            "invoice_date", "paid_at", "created_by",
        ]
        read_only_fields = ["created_by"]  # BR-PQ-16
