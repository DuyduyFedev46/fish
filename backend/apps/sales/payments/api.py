"""
API nội bộ — hoá đơn bán (READ-ONLY, BR-PQ-11) + hàng chờ giao dịch lệch.

Xác nhận thanh toán thủ công (E-05, BR-TT-08) nay gắn vào ĐƠN:
`POST /api/sales/orders/{id}/confirm-payment` (orders/api.py, S11). Action cũ trên hoá đơn
đã gỡ — đơn chưa trả thì chưa có hoá đơn để bấm (A2).
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.api import BusinessModelPermissions, StandardPagination, require_perm
from apps.sales.models import PaymentTransaction, SalesInvoice

from . import services
from .serializers import PaymentTransactionSerializer, SalesInvoiceSerializer


class SalesInvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SalesInvoice.objects.select_related("customer", "sales_order").all()
    serializer_class = SalesInvoiceSerializer
    permission_classes = [BusinessModelPermissions]


class PaymentTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    S12 — hàng chờ thanh toán lệch (UNDERPAID/ORPHAN/UNMATCHED/OVERPAID), BR-TT-09.

    `GET /api/sales/payments/?resolution_status=OPEN[,RESOLVED]&match_status=…&page=`
    `GET /api/sales/payments/{id}/`
    `POST /api/sales/payments/{id}/resolve` {"action": "ATTACH_TO_ORDER"|"CONFIRM_ORDER", "order_id", "note"}

    Mọi thao tác (kể cả xem) đòi `sales.confirm_payment_manual` — hàng chờ lệch là việc của
    Chủ (BR-TT-07, S12-AC7). Quản lý vẫn thấy giao dịch của đơn trong chi tiết đơn (S10).
    """

    queryset = PaymentTransaction.objects.select_related(
        "sales_order", "resolved_by__staff_profile"
    ).all()
    serializer_class = PaymentTransactionSerializer
    permission_classes = [BusinessModelPermissions]
    pagination_class = StandardPagination
    custom_perm_actions = ("resolve",)

    def check_permissions(self, request):
        super().check_permissions(request)  # 401 khi chưa đăng nhập
        require_perm(request.user, services.RESOLVE_PERM)

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if self.action != "list":
            return queryset
        params = self.request.query_params
        for name in ("resolution_status", "match_status"):
            values = [v.strip().upper() for v in params.get(name, "").split(",") if v.strip()]
            if values:
                queryset = queryset.filter(**{f"{name}__in": values})
        return queryset

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        """S12: gắn đơn / xác nhận đơn khi khách đã bù (BR-TT-09). Hoàn tiền: tạo phiếu hoàn (S13)."""
        data = request.data if hasattr(request.data, "get") else {}
        result = services.resolve_payment(
            payment=self.get_object(),
            action=data.get("action"),
            order_id=data.get("order_id"),
            note=data.get("note", ""),
            actor=request.user,
        )
        return Response(result)
