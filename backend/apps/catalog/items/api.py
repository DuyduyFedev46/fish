"""API nội bộ — nhóm hàng, mặt hàng, công thức combo (P-01). CRUD theo perm model (Tầng 1)."""
from rest_framework import viewsets

from apps.catalog.models import BundleLine, Item, ItemGroup
from apps.common.api import BusinessModelPermissions

from .serializers import BundleLineSerializer, ItemGroupSerializer, ItemSerializer


class ItemGroupViewSet(viewsets.ModelViewSet):
    queryset = ItemGroup.objects.all()
    serializer_class = ItemGroupSerializer
    permission_classes = [BusinessModelPermissions]


class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.select_related("item_group").all()
    serializer_class = ItemSerializer
    permission_classes = [BusinessModelPermissions]


class BundleLineViewSet(viewsets.ModelViewSet):
    queryset = BundleLine.objects.select_related("bundle", "component").all()
    serializer_class = BundleLineSerializer
    permission_classes = [BusinessModelPermissions]
