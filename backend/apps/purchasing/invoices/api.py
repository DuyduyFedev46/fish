"""API nội bộ — hoá đơn mua (BR-MH-04). CRUD theo perm model; người tạo = người đăng nhập (BR-PQ-16)."""
from apps.common.api import BusinessModelPermissions, DocumentViewSet
from apps.purchasing.models import PurchaseInvoice

from .serializers import PurchaseInvoiceSerializer


class PurchaseInvoiceViewSet(DocumentViewSet):
    queryset = PurchaseInvoice.objects.select_related("supplier", "receipt").all()
    serializer_class = PurchaseInvoiceSerializer
    permission_classes = [BusinessModelPermissions]
    actor_fields = ("created_by",)  # BR-PQ-16
