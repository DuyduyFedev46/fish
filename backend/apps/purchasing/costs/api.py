"""
API nội bộ — chi phí mua hàng (P-03). Ghi chi phí đổi giá vốn lô → chỉ Chủ
(builtin add_purchasecost). Người tạo = người đăng nhập (BR-PQ-16).

R12 (ERP theo design Lô 12): `GET /api/purchasing/costs/?cost_type=ICE,TRANSPORT&month=YYYY-MM&page=` (20 dòng/trang) và
`GET …/{id}/`. Tiền chi phí phụ là giá vốn: đọc cần `view_purchasecost` (Tầng 1, chỉ owner) VÀ `view_costprice`
(bất biến 1). Sai tham số lọc → 400.
"""
from decimal import Decimal

from rest_framework.response import Response

from apps.common.api import (
    VIEW_COSTPRICE_PERM, BusinessModelPermissions, DocumentViewSet, StandardPagination, require_perm,
)
from apps.purchasing.models import PurchaseCost

from . import services
from .filters import filter_costs
from .serializers import PurchaseCostSerializer


class PurchaseCostViewSet(DocumentViewSet):
    queryset = PurchaseCost.objects.prefetch_related("allocations").all()
    serializer_class = PurchaseCostSerializer
    permission_classes = [BusinessModelPermissions]
    pagination_class = StandardPagination
    actor_fields = ("created_by",)  # BR-PQ-16

    def check_permissions(self, request):
        super().check_permissions(request)  # 401 chưa đăng nhập, 403 thiếu quyền model
        if request.method in ("GET", "HEAD"):
            # Chứng từ chi phí phụ là giá vốn: không có field nào để ẩn từng phần → chặn cả request.
            require_perm(request.user, VIEW_COSTPRICE_PERM)

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if self.action == "list":
            queryset = filter_costs(queryset, self.request.query_params)
        return queryset

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
