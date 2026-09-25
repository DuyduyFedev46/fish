"""
API nội bộ — chi phí mua hàng (P-03). Ghi chi phí đổi giá vốn lô → chỉ Chủ
(builtin add_purchasecost). Người tạo = người đăng nhập (BR-PQ-16).
"""
from decimal import Decimal

from rest_framework.response import Response

from apps.common.api import BusinessModelPermissions, DocumentViewSet, require_perm
from apps.purchasing.models import PurchaseCost

from . import services
from .serializers import PurchaseCostSerializer


class PurchaseCostViewSet(DocumentViewSet):
    queryset = PurchaseCost.objects.prefetch_related("allocations").all()
    serializer_class = PurchaseCostSerializer
    permission_classes = [BusinessModelPermissions]
    actor_fields = ("created_by",)  # BR-PQ-16

    def create(self, request, *args, **kwargs):
        # Ghi chi phí + phân bổ vào giá vốn lô — chỉ Chủ (add_purchasecost builtin).
        require_perm(request.user, "purchasing.add_purchasecost")
        self.reject_protected_fields(request.data)
        d = request.data or {}
        cost = services.record_purchase_cost(
            cost_type=d.get("cost_type"),
            amount=Decimal(str(d.get("amount"))),
            allocation_method=d.get("allocation_method", PurchaseCost.AllocationMethod.BY_QTY),
            incurred_date=d.get("incurred_date"),
            allocations=d.get("allocations") or [],
            actor=request.user,
            note=d.get("note", ""),
        )
        return Response(self.get_serializer(cost).data, status=201)
