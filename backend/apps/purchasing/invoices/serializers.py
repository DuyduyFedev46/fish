"""
Serializer hoá đơn mua (BR-MH-04, R11).

D-3 (Duy chốt, 02b §6 Q3): Quản lý THẤY `amount`. Người xem được hoá đơn mua là người có `view_purchaseinvoice`
(owner, manager); vai khác bị chặn ở Tầng 1 (403) nên serializer không ẩn field nào. `amount` vì thế không nằm trong
`COST_KEYS`.
"""
from rest_framework import serializers

from apps.purchasing.models import PurchaseInvoice


class PurchaseInvoiceSerializer(serializers.ModelSerializer):
    code = serializers.SerializerMethodField()
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    receipt_code = serializers.SerializerMethodField()
    is_paid_label = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseInvoice
        fields = [
            "id", "code", "supplier", "supplier_name", "receipt", "receipt_code", "amount",
            "is_paid", "is_paid_label", "invoice_date", "paid_at", "created_by",
        ]
        read_only_fields = ["created_by"]  # BR-PQ-16

    def get_code(self, invoice):
        return f"#{invoice.pk}"

    def get_receipt_code(self, invoice):
        return f"PR-{invoice.receipt_id}" if invoice.receipt_id else None

    def get_is_paid_label(self, invoice):
        return "Đã trả tiền" if invoice.is_paid else "Chưa trả tiền"
