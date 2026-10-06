"""
Serializer hoá đơn mua (BR-MH-04, R11).

D-3 (Duy chốt, 02b §6 Q3): Quản lý THẤY `amount`. Người xem được hoá đơn mua là người có `view_purchaseinvoice`
(owner, manager); vai khác bị chặn ở Tầng 1 (403) nên serializer không ẩn field nào. `amount` vì thế không nằm trong
`COST_KEYS`.
"""
from django.utils import timezone
from rest_framework import serializers

from apps.common.exceptions import BusinessError
from apps.purchasing.models import PurchaseInvoice, PurchaseReceipt


class PurchaseInvoiceSerializer(serializers.ModelSerializer):
    code = serializers.SerializerMethodField()
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    receipt_code = serializers.SerializerMethodField()
    is_paid_label = serializers.SerializerMethodField()
    # Khai tường minh để KHÔNG kế thừa MinValueValidator(0) của model: `validate()` kiểm `amount > 0` và trả mã
    # AMOUNT_NOT_POSITIVE (QA12-N3) thay vì câu lỗi tiếng Anh của DRF.
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        model = PurchaseInvoice
        fields = [
            "id", "code", "supplier", "supplier_name", "receipt", "receipt_code", "amount",
            "is_paid", "is_paid_label", "invoice_date", "paid_at", "created_by",
        ]
        read_only_fields = ["created_by"]  # BR-PQ-16

    def validate_receipt(self, receipt):
        """Không gắn hoá đơn vào phiếu nhập đã huỷ (BR-MH-07, BR-PQ-10): 400 `RECEIPT_CANCELLED`."""
        if receipt is not None and receipt.status == PurchaseReceipt.Status.CANCELLED:
            raise BusinessError(
                "Phiếu nhập đã huỷ, không gắn hoá đơn mua vào được (BR-MH-07).", code="RECEIPT_CANCELLED"
            )
        return receipt

    def validate(self, attrs):
        """
        Luật ghi hoá đơn mua trên giá trị ĐÃ GỘP (`attrs` đè lên dòng cũ khi sửa), Lô 17a (BR-MH-03, BR-MH-04).

        Chỉ kiểm phần người gọi đụng tới: PATCH không gửi `is_paid`/`paid_at` thì bỏ qua luật `paid_at`, để dòng cũ
        `is_paid=True, paid_at=NULL` vẫn sửa được số tiền. Câu lỗi tiếng Việt, không kèm mã BR.
        """
        instance = self.instance

        def merged(name):
            if name in attrs:
                return attrs[name]
            return getattr(instance, name) if instance is not None else None

        creating = instance is None
        if creating or "amount" in attrs:
            amount = merged("amount")
            if amount is None or amount <= 0:
                raise BusinessError("Số tiền hoá đơn phải lớn hơn 0.", code="AMOUNT_NOT_POSITIVE")

        if creating or "receipt" in attrs or "supplier" in attrs:
            receipt, supplier = merged("receipt"), merged("supplier")
            if receipt is not None and supplier is not None and receipt.supplier_id != supplier.pk:
                raise BusinessError(
                    "Phiếu nhập thuộc nhà cung cấp khác, không gắn vào hoá đơn của nhà cung cấp này được.",
                    code="INVOICE_SUPPLIER_MISMATCH",
                )

        if creating or "is_paid" in attrs or "paid_at" in attrs:
            is_paid = attrs.get("is_paid", instance.is_paid if instance is not None else True)  # mặc định model: đã trả
            paid_at = merged("paid_at")
            if is_paid and paid_at is None:
                raise BusinessError("Hoá đơn đã trả tiền thì phải có thời điểm trả.", code="PAID_AT_REQUIRED")
            if not is_paid and paid_at is not None:
                raise BusinessError(
                    "Hoá đơn chưa trả tiền thì không có thời điểm trả.", code="PAID_AT_WHEN_UNPAID"
                )
            if paid_at is not None and paid_at > timezone.now():
                raise BusinessError("Thời điểm trả tiền không được ở tương lai.", code="PAID_AT_IN_FUTURE")
        return attrs

    def get_code(self, invoice):
        return f"#{invoice.pk}"

    def get_receipt_code(self, invoice):
        return f"PR-{invoice.receipt_id}" if invoice.receipt_id else None

    def get_is_paid_label(self, invoice):
        return "Đã trả tiền" if invoice.is_paid else "Chưa trả tiền"
