"""
API nội bộ — khách hàng. Tầng 3 (BR-PQ-12, SR-PII-01/02, bất biến 9):
- Chủ, Quản lý, superuser: toàn bộ danh bạ, đủ field.
- NV kho không có `sales.view_customer` (data migration accounts/0012) nên bị 403. Người kiêm nhiệm
  NV kho + NV giao có quyền xem khách qua nv_giao nên cũng chỉ thấy khách của phiếu giao gán cho mình.
- NV giao: chỉ khách của phiếu gán cho mình còn trong cửa sổ `DELIVERY_PII_RECENT_DAYS` (pii_scope.py),
  chỉ field cần để giao (`id`, `phone`, `name`, `created_at`), không có `note`, `default_address`.
  Ngoài phạm vi → 404 (không lộ bản ghi có tồn tại).
"""
from rest_framework import viewsets

from apps.common.api import BusinessModelPermissions, NoStoreMixin, sees_customer_directory
from apps.delivery.models import DeliveryNote
from apps.delivery.pii_scope import courier_visible_note_q
from apps.sales.models import Customer

from .serializers import CourierCustomerSerializer, CustomerSerializer


class CustomerViewSet(NoStoreMixin, viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [BusinessModelPermissions]

    def get_serializer_class(self):
        if sees_customer_directory(self.request.user):
            return CustomerSerializer
        return CourierCustomerSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if sees_customer_directory(user):
            return qs
        visible_notes = DeliveryNote.objects.filter(courier_visible_note_q(user))
        return qs.filter(orders__invoice__delivery_notes__in=visible_notes).distinct()
