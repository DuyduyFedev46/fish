"""API nội bộ — kiểm kê (P-09). Tầng 2: approve_stockreconciliation; người duyệt ≠ người nhập (BR-KK-02)."""
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.api import BusinessModelPermissions, DocumentViewSet, require_perm
from apps.inventory.models import StockReconciliation

from . import services
from .serializers import StockReconciliationSerializer


class StockReconciliationViewSet(DocumentViewSet):
    queryset = StockReconciliation.objects.prefetch_related("lines").all()
    serializer_class = StockReconciliationSerializer
    permission_classes = [BusinessModelPermissions]
    custom_perm_actions = ("approve",)
    locked_fields = ("status", "approved_by", "approved_at")  # BR-PQ-14
    actor_fields = ("created_by",)  # BR-PQ-16 → BR-KK-02 có nghĩa

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        require_perm(request.user, "inventory.approve_stockreconciliation")
        rec = services.apply_reconciliation(reconciliation=self.get_object(), approver=request.user)
        return Response(self.get_serializer(rec).data)
