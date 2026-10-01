"""
API nội bộ — hoá đơn mua (BR-MH-04). CRUD theo perm model; người tạo = người đăng nhập (BR-PQ-16).

R11 (ERP theo design Lô 12): `GET /api/purchasing/invoices/?is_paid=&supplier=&month=YYYY-MM&page=` (20 dòng/trang) và
`GET …/{id}/`. Quyền `view_purchaseinvoice` (owner, manager). D-3: Quản lý thấy `amount`. Sai tham số lọc → 400.
"""
from apps.common.api import BusinessModelPermissions, DocumentViewSet, StandardPagination
from apps.purchasing.models import PurchaseInvoice

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
