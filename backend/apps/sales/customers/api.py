"""
API nội bộ — khách hàng. Tầng 3 (BR-PQ-12/35, SR-PII-01/02, bất biến 9), phạm vi D7 từ cấu hình nhóm (PV-05, `scope.py`),
cùng hàm với danh bạ khách mới (hai API trả cùng một tập khách):
- D7 = `all` (Chủ, Quản lý mặc định, superuser): toàn bộ danh bạ, đủ field.
- D7 = `assigned_deliveries` (NV giao mặc định): chỉ khách của phiếu gán cho mình còn trong cửa sổ `DELIVERY_PII_RECENT_DAYS`
  (pii_scope.py), chỉ field cần để giao (`id`, `phone`, `name`, `created_at`), không có `note`, `default_address`.
- D7 = `none`: danh sách rỗng, chi tiết 404.
- NV kho không có `sales.view_customer` (data migration accounts/0012) nên bị 403 (cổng Tầng 1 đứng trước).
  Ngoài phạm vi → 404 (không lộ bản ghi có tồn tại).
"""
from rest_framework import viewsets

from apps.common.api import BusinessModelPermissions, NoStoreMixin
from apps.sales.models import Customer

from .scope import scope_customers_for, sees_all_customers
from .serializers import CourierCustomerSerializer, CustomerSerializer


class CustomerViewSet(NoStoreMixin, viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [BusinessModelPermissions]

    def get_serializer_class(self):
        if sees_all_customers(self.request.user):
            return CustomerSerializer
        return CourierCustomerSerializer

    def get_queryset(self):
        return scope_customers_for(self.request.user, super().get_queryset())
