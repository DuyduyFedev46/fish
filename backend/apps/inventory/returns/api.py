"""API nội bộ — hàng giao thất bại về kho (P-08). Tầng 2: approve_returntostock (BR-HV-02)."""
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.api import BusinessModelPermissions, DocumentViewSet, require_perm
from apps.inventory.models import ReturnToStock

from . import services
from .serializers import ReturnToStockSerializer


class ReturnToStockViewSet(DocumentViewSet):
    queryset = ReturnToStock.objects.select_related("batch").all()
    serializer_class = ReturnToStockSerializer
    permission_classes = [BusinessModelPermissions]
    custom_perm_actions = ("approve",)
    locked_fields = ("status", "decision", "approved_by")  # BR-PQ-14 (tạo mới qua S22)
    actor_fields = ("created_by",)  # BR-PQ-16

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        require_perm(request.user, "inventory.approve_returntostock")
        rt = self.get_object()
        decision = request.data.get("decision")
        if decision in (ReturnToStock.Decision.RESTOCK, ReturnToStock.Decision.WRITE_OFF):
            rt.decision = decision
            rt.save(update_fields=["decision"])
        rt = services.apply_return(return_to_stock=rt, approver=request.user)
        return Response(self.get_serializer(rt).data)
