"""API nội bộ — khách hàng. Tầng 3: nv_giao chỉ thấy khách của phiếu giao gán cho mình (BR-PQ-12)."""
from rest_framework import viewsets

from apps.common.api import BusinessModelPermissions, has_full_delivery_scope
from apps.sales.models import Customer

from .serializers import CustomerSerializer


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [BusinessModelPermissions]

    def get_queryset(self):
        # S5 / BR-PQ-12: nv_giao chỉ thấy khách của đơn thuộc phiếu gán cho mình;
        # ngoài phạm vi → 404 (không lộ bản ghi có tồn tại).
        qs = super().get_queryset()
        user = self.request.user
        if has_full_delivery_scope(user):
            return qs
        return qs.filter(orders__invoice__delivery_notes__assigned_to=user).distinct()
