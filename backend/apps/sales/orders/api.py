"""
API nội bộ — đơn hàng. READ-ONLY (Hệ thống tạo, BR-PQ-11). Tầng 2: cancel_paid_order.
Tầng 3: nv_giao chỉ thấy đơn của phiếu giao gán cho mình (BR-PQ-12).
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.api import BusinessModelPermissions, has_full_delivery_scope, require_perm
from apps.sales.models import SalesOrder

from . import services
from .serializers import SalesOrderSerializer


class SalesOrderViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SalesOrder.objects.select_related("customer").prefetch_related("lines").all()
    serializer_class = SalesOrderSerializer
    permission_classes = [BusinessModelPermissions]
    custom_perm_actions = ("cancel",)

    def get_queryset(self):
        # S5 / BR-PQ-12: nv_giao chỉ thấy đơn của phiếu giao gán cho mình.
        qs = super().get_queryset()
        user = self.request.user
        if has_full_delivery_scope(user):
            return qs
        return qs.filter(invoice__delivery_notes__assigned_to=user).distinct()

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        require_perm(request.user, "sales.cancel_paid_order")
        order = services.cancel_paid_order(
            order=self.get_object(), actor=request.user, reason=request.data.get("reason", "")
        )
        return Response(self.get_serializer(order).data)
