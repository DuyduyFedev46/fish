"""
API nội bộ — hoá đơn mua (BR-MH-04). CRUD theo perm model; người tạo = người đăng nhập (BR-PQ-16).

R11 (ERP theo design Lô 12): `GET /api/purchasing/invoices/?is_paid=&supplier=&month=YYYY-MM&page=` (20 dòng/trang) và
`GET …/{id}/`. Quyền `view_purchaseinvoice` (owner, manager). D-3: Quản lý thấy `amount`. Sai tham số lọc → 400.
"""
from django.db import transaction

from apps.common.api import BusinessModelPermissions, DocumentViewSet, StandardPagination
from apps.common.exceptions import BusinessError
from apps.purchasing.models import PurchaseInvoice, PurchaseReceipt

from .filters import filter_invoices
from .serializers import PurchaseInvoiceSerializer


class PurchaseInvoiceViewSet(DocumentViewSet):
    queryset = PurchaseInvoice.objects.select_related("supplier", "receipt").all()
    serializer_class = PurchaseInvoiceSerializer
    permission_classes = [BusinessModelPermissions]
    pagination_class = StandardPagination
    actor_fields = ("created_by",)  # BR-PQ-16

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if self.action == "list":
            queryset = filter_invoices(queryset, self.request.query_params)
        return queryset

    def _save_locking_receipt(self, serializer, **extra):
        """
        Khoá phiếu nhập rồi kiểm lại trạng thái cùng transaction với lúc lưu, để huỷ phiếu song song
        không lọt hoá đơn vào phiếu vừa huỷ (BR-MH-07; `cancel_receipt` cũng khoá phiếu).
        """
        with transaction.atomic():
            receipt = serializer.validated_data.get("receipt")
            if receipt is not None:
                locked = PurchaseReceipt.objects.select_for_update().get(pk=receipt.pk)
                if locked.status == PurchaseReceipt.Status.CANCELLED:
                    raise BusinessError(
                        "Phiếu nhập đã huỷ, không gắn hoá đơn mua vào được (BR-MH-07).", code="RECEIPT_CANCELLED"
                    )
            serializer.save(**extra)

    def perform_create(self, serializer):
        self._save_locking_receipt(serializer, **{f: self.request.user for f in self.actor_fields})

    def perform_update(self, serializer):
        self._save_locking_receipt(serializer)
