"""
API nội bộ — nhà cung cấp & phiếu nhập (P-02). Action submit sinh lô; status khoá
(BR-PQ-14), người tạo = người đăng nhập (BR-PQ-16).
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.api import BusinessModelPermissions, DocumentViewSet, require_perm
from apps.purchasing.models import PurchaseReceipt, Supplier

from . import services
from .serializers import PurchaseReceiptSerializer, SupplierSerializer


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [BusinessModelPermissions]


class PurchaseReceiptViewSet(DocumentViewSet):
    queryset = PurchaseReceipt.objects.prefetch_related("lines").all()
    serializer_class = PurchaseReceiptSerializer
    permission_classes = [BusinessModelPermissions]
    custom_perm_actions = ("submit",)
    locked_fields = ("status",)  # BR-PQ-14: ghi nhận qua action submit
    actor_fields = ("created_by",)  # BR-PQ-16

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        # Sinh lô từ các dòng nhập (cần quyền change phiếu — Tầng 1 đã chặn).
        require_perm(request.user, "purchasing.change_purchasereceipt")
        batches = services.submit_receipt(receipt=self.get_object(), actor=request.user)
        return Response(
            {"receipt": self.get_serializer(self.get_object()).data,
             "batches_created": [b.batch_id for b in batches]}
        )
