"""API nội bộ — nhóm hàng, mặt hàng, công thức combo (P-01). CRUD theo perm model (Tầng 1)."""
from django.db.models import Count
from rest_framework import viewsets

from apps.ai.declare import AiMeta
from apps.catalog.models import BundleLine, Item, ItemGroup
from apps.catalog.pricing.services import prefetch_current_prices
from apps.common.api import BusinessModelPermissions

from .filters import bool_param, choice_param, id_param
from .serializers import BundleLineSerializer, ItemGroupSerializer, ItemSerializer, can_view_item_price


class ItemGroupViewSet(viewsets.ModelViewSet):
    # R14: `parent_name` cần `parent`; `item_count` đếm bằng một truy vấn (không N+1).
    queryset = ItemGroup.objects.select_related("parent").annotate(item_count=Count("items"))
    serializer_class = ItemGroupSerializer
    permission_classes = [BusinessModelPermissions]


class ItemViewSet(viewsets.ModelViewSet):
    ai = AiMeta(keywords=("tra hàng",))
    queryset = Item.objects.select_related("item_group").prefetch_related("bundle_lines__component")
    serializer_class = ItemSerializer
    permission_classes = [BusinessModelPermissions]

    def get_queryset(self):
        # A2-AC16: bộ lọc "Chưa có ảnh" cho UC-A5 (nhập ảnh ban đầu cho toàn bộ danh mục).
        qs = super().get_queryset().select_related("image")
        if can_view_item_price(self.request):  # R14/T9: chỉ nạp giá bán khi người xem được phép thấy
            qs = qs.prefetch_related(prefetch_current_prices())
        if self.action == "list":
            qs = self.filter_list(qs)
        return qs

    def filter_list(self, qs):
        """R14: `item_group=<id>`, `is_active=1|0`, `item_type=SIMPLE|BUNDLE`, `has_image=1|0`. Rỗng = không lọc; sai → 400 INVALID_FILTER."""
        params = self.request.query_params
        group = id_param(params, "item_group")
        if group is not None:
            qs = qs.filter(item_group_id=group)
        is_active = bool_param(params, "is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        has_image = bool_param(params, "has_image")  # A2-AC16; sai giá trị → 400 như các bộ lọc khác (L5)
        if has_image is not None:
            qs = qs.filter(image__isnull=not has_image)
        item_type = choice_param(params, "item_type", Item.ItemType.values)
        if item_type is not None:
            qs = qs.filter(item_type=item_type)
        return qs


class BundleLineViewSet(viewsets.ModelViewSet):
    queryset = BundleLine.objects.select_related("bundle", "component").all()
    serializer_class = BundleLineSerializer
    permission_classes = [BusinessModelPermissions]
