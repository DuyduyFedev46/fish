"""API nội bộ — nhóm hàng, mặt hàng, công thức combo (P-01). CRUD theo perm model (Tầng 1)."""
from rest_framework import viewsets

from apps.ai.declare import AiMeta
from apps.catalog.models import BundleLine, Item, ItemGroup
from apps.common.api import BusinessModelPermissions

from .serializers import BundleLineSerializer, ItemGroupSerializer, ItemSerializer


class ItemGroupViewSet(viewsets.ModelViewSet):
    queryset = ItemGroup.objects.all()
    serializer_class = ItemGroupSerializer
    permission_classes = [BusinessModelPermissions]


class ItemViewSet(viewsets.ModelViewSet):
    ai = AiMeta(keywords=("tra hàng",))
    queryset = Item.objects.select_related("item_group").all()
    serializer_class = ItemSerializer
    permission_classes = [BusinessModelPermissions]

    def get_queryset(self):
        # A2-AC16: bộ lọc "Chưa có ảnh" cho UC-A5 (nhập ảnh ban đầu cho toàn bộ danh mục).
        qs = super().get_queryset().select_related("image")
        has_image = self.request.query_params.get("has_image")
        if has_image is not None:
            wants_image = has_image.strip().lower() in {"1", "true", "yes"}
            qs = qs.filter(image__isnull=not wants_image)
        return qs


class BundleLineViewSet(viewsets.ModelViewSet):
    queryset = BundleLine.objects.select_related("bundle", "component").all()
    serializer_class = BundleLineSerializer
    permission_classes = [BusinessModelPermissions]
