"""API nội bộ — nhóm hàng, mặt hàng, công thức combo (P-01). CRUD theo perm model (Tầng 1)."""
from django.db.models import Count
from rest_framework import viewsets

from apps.ai.declare import AiMeta
from apps.catalog.models import BundleLine, Item, ItemGroup
from apps.catalog.pricing.services import prefetch_current_prices
from apps.common.api import BusinessModelPermissions
from apps.common.audit import record_audit

from .filters import apply_item_filters
from .serializers import BundleLineSerializer, ItemGroupSerializer, ItemSerializer, can_view_item_price


class ItemGroupViewSet(viewsets.ModelViewSet):
    # R14: `parent_name` cần `parent`; `item_count` đếm bằng một truy vấn (không N+1).
    queryset = ItemGroup.objects.select_related("parent").annotate(item_count=Count("items"))
    serializer_class = ItemGroupSerializer
    permission_classes = [BusinessModelPermissions]

    def perform_update(self, serializer):
        """SHOP-2b-02 AC1: đổi slug thì ghi AuditLog trước → sau (BR-PQ-04). Slug là mã đường dẫn, không phải dữ liệu cá nhân."""
        old_slug = serializer.instance.slug
        group = serializer.save()
        if group.slug != old_slug:
            record_audit("update_itemgroup", actor=self.request.user, obj=group,
                         changes={"slug": {"from": old_slug, "to": group.slug}})


class ItemViewSet(viewsets.ModelViewSet):
    ai = AiMeta(keywords=("tra hàng",))
    queryset = Item.objects.select_related("item_group").prefetch_related("bundle_lines__component")
    serializer_class = ItemSerializer
    permission_classes = [BusinessModelPermissions]

    def perform_update(self, serializer):
        """SHOP-2b-01 AC6: ghi AuditLog `update_item` chỉ với TÊN trường đã đổi, không chép chữ tự do (bất biến 9)."""
        instance = serializer.instance
        before = {name: getattr(instance, name) for name in serializer.validated_data if hasattr(instance, name)}
        item = serializer.save()
        changed = sorted(name for name, old in before.items() if getattr(item, name) != old)
        if changed:
            record_audit("update_item", actor=self.request.user, obj=item, changes={"fields": changed})

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
        return apply_item_filters(qs, self.request.query_params)


class BundleLineViewSet(viewsets.ModelViewSet):
    queryset = BundleLine.objects.select_related("bundle", "component").all()
    serializer_class = BundleLineSerializer
    permission_classes = [BusinessModelPermissions]
