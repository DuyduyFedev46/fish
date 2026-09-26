"""Serializer nhóm hàng, mặt hàng, công thức combo (không có field giá vốn)."""
from rest_framework import serializers

from apps.catalog.images.serializers import serialize_item_image
from apps.catalog.models import BundleLine, Item, ItemGroup


class ItemGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemGroup
        fields = ["id", "name", "parent"]


class BundleLineSerializer(serializers.ModelSerializer):
    component_code = serializers.CharField(source="component.code", read_only=True)
    component_name = serializers.CharField(source="component.name", read_only=True)

    class Meta:
        model = BundleLine
        fields = ["id", "bundle", "component", "component_code", "component_name", "qty_per_bundle"]


class ItemSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source="item_group.name", read_only=True)
    bundle_lines = BundleLineSerializer(many=True, read_only=True)
    # A2 contract mục 2: object ảnh như response upload nhưng bỏ `uploaded_by`, hoặc null.
    image = serializers.SerializerMethodField()

    class Meta:
        model = Item
        fields = [
            "id", "code", "name", "item_group", "group_name", "item_type",
            "stock_uom", "shelf_life_in_days", "has_batch_no", "has_expiry_date",
            "is_active", "description", "bundle_lines", "image",
        ]

    def get_image(self, obj):
        return serialize_item_image(getattr(obj, "image", None), include_uploaded_by=False)
