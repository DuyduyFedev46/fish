"""
API nội bộ — bảng giá, giá niêm yết theo hiệu lực, ưu đãi 1 tầng (P-01). Thêm/sửa theo perm model (Tầng 1), không xoá cứng (DELETE → 405).

T9: Chủ có đủ quyền ghi `ItemPrice` và `PricingRule`; Quản lý chỉ xem (403 khi ghi); `warehouse_staff` không có
quyền xem giá nên 403 cả khi đọc. R14: lọc `item-prices?item=`, `pricing-rules?is_active=&apply_on=`.
"""
from rest_framework import viewsets
from rest_framework.exceptions import MethodNotAllowed

from apps.catalog.items.filters import bool_param, choice_param, id_param
from apps.catalog.models import ItemPrice, PriceList, PricingRule
from apps.common.api import BusinessModelPermissions

from . import services
from .serializers import ItemPriceSerializer, PriceListSerializer, PricingRuleSerializer


class NoHardDeleteMixin:
    """Bảng giá, giá niêm yết, ưu đãi không xoá cứng (BR-PQ-10, bất biến 3): ưu đãi tắt bằng `is_active=false`,
    giá đóng bằng ngày kết thúc. DELETE trả 405 cho mọi người đã đăng nhập (kể cả người thiếu quyền `delete_*`,
    thống nhất với `SupplierViewSet`), người chưa đăng nhập vẫn nhận 401. Không bao giờ chạm tới ProtectedError."""

    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def check_permissions(self, request):
        if request.user.is_authenticated and request.method.lower() not in self.http_method_names:
            raise MethodNotAllowed(request.method)
        super().check_permissions(request)


class PriceListViewSet(NoHardDeleteMixin, viewsets.ModelViewSet):
    queryset = PriceList.objects.order_by("id")
    serializer_class = PriceListSerializer
    permission_classes = [BusinessModelPermissions]


class ItemPriceViewSet(NoHardDeleteMixin, viewsets.ModelViewSet):
    queryset = ItemPrice.objects.select_related("item", "price_list").all()
    serializer_class = ItemPriceSerializer
    permission_classes = [BusinessModelPermissions]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "list":
            item = id_param(self.request.query_params, "item")
            if item is not None:
                qs = qs.filter(item_id=item)
        return qs

    def perform_create(self, serializer):
        """ED-31-AC1: đặt giá mới tự đóng giá cũ, chặn chồng lấn (BR-DM-03) — logic ở `services.set_item_price`."""
        serializer.instance = services.set_item_price(actor=self.request.user, **serializer.validated_data)

    def perform_update(self, serializer):
        serializer.instance = services.update_item_price(
            price=serializer.instance, changes=serializer.validated_data, actor=self.request.user
        )


class PricingRuleViewSet(NoHardDeleteMixin, viewsets.ModelViewSet):
    queryset = PricingRule.objects.select_related("item").order_by("id")
    serializer_class = PricingRuleSerializer
    permission_classes = [BusinessModelPermissions]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "list":
            params = self.request.query_params
            is_active = bool_param(params, "is_active")
            if is_active is not None:
                qs = qs.filter(is_active=is_active)
            apply_on = choice_param(params, "apply_on", PricingRule.ApplyOn.values)
            if apply_on is not None:
                qs = qs.filter(apply_on=apply_on)
        return qs
