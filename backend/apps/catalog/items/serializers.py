"""
Serializer nhóm hàng, mặt hàng, công thức combo (không có field giá vốn).

`current_price` là giá BÁN đang hiệu lực (R14), chỉ cho người có `catalog.view_itemprice` (T9: Chủ, Quản lý);
`warehouse_staff` không có quyền này nên field bị bỏ hẳn khỏi JSON.
"""
import re

from rest_framework import serializers

from apps.catalog.images.serializers import serialize_item_image
from apps.catalog.models import BundleLine, Item, ItemGroup
from apps.catalog.pricing.services import CURRENT_PRICES_ATTR, current_item_price
from apps.common.slugs import SLUG_MAX_LENGTH, slugify_vi, unique_slug

from .public_text import PUBLIC_TEXT_LIMITS, public_text_error

VIEW_ITEM_PRICE_PERM = "catalog.view_itemprice"


def can_view_item_price(request) -> bool:
    """Không có request (gọi nội bộ) thì mặc định ẩn."""
    user = getattr(request, "user", None)
    return bool(user and user.has_perm(VIEW_ITEM_PRICE_PERM))


SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class ItemGroupSerializer(serializers.ModelSerializer):
    # SHOP-2b-02: bỏ trống khi tạo thì tự sinh từ tên; khi sửa không được để trống.
    slug = serializers.CharField(required=False, allow_blank=True, max_length=SLUG_MAX_LENGTH, trim_whitespace=True)
    parent_name = serializers.CharField(source="parent.name", read_only=True, default=None)
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = ItemGroup
        fields = ["id", "name", "slug", "parent", "parent_name", "item_count"]

    def validate_slug(self, value):
        value = (value or "").strip()
        if not value:
            if self.instance is not None:
                raise serializers.ValidationError("Không được để trống.")
            return value  # tạo mới: `create` tự sinh
        if not SLUG_PATTERN.match(value):
            raise serializers.ValidationError("Chỉ dùng chữ thường không dấu, số và dấu gạch ngang.")
        taken = ItemGroup.objects.filter(slug=value)
        if self.instance is not None:
            taken = taken.exclude(pk=self.instance.pk)
        if taken.exists():
            raise serializers.ValidationError("Đường dẫn đã dùng cho nhóm khác.")
        return value

    def create(self, validated_data):
        if not validated_data.get("slug"):
            validated_data["slug"] = unique_slug(ItemGroup, slugify_vi(validated_data.get("name")))
        return super().create(validated_data)

    def validate_parent(self, parent):
        """N13-3: nhóm không được chọn chính nó hoặc nhóm con/cháu của nó làm nhóm cha (chống vòng)."""
        if parent is None or self.instance is None:
            return parent
        seen, node = set(), parent
        while node is not None and node.pk not in seen:
            if node.pk == self.instance.pk:
                raise serializers.ValidationError(
                    "Không thể chọn nhóm này hoặc nhóm con của nó làm nhóm cha. Hãy chọn nhóm cha khác."
                )
            seen.add(node.pk)
            node = node.parent
        return parent

    def get_item_count(self, obj) -> int:
        """Số mặt hàng thuộc nhóm (kể cả đang ẩn). View danh sách đã annotate; bản ghi vừa tạo thì đếm."""
        annotated = getattr(obj, "item_count", None)
        return annotated if annotated is not None else obj.items.count()


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
    current_price = serializers.SerializerMethodField()

    class Meta:
        model = Item
        fields = [
            "id", "code", "name", "item_group", "group_name", "item_type",
            "stock_uom", "shelf_life_in_days", "has_batch_no", "has_expiry_date",
            "is_active", "description", "short_note", "spec", "storage", "origin",
            "bundle_lines", "image", "current_price",
        ]
        # Thông điệp tiếng Việt thay câu mặc định của max_length (SHOP-2b-01 AC4).
        extra_kwargs = {
            name: {"error_messages": {"max_length": "Tối đa {max_length} ký tự."}}
            for name in ("short_note", "spec", "storage", "origin")
        }

    def _validate_public_text(self, field, value):
        """SHOP-2b-01, BR-DM-25: độ dài và chữ công khai (không SĐT, giá, mã lô, nhà cung cấp/tàu/ngày nhập)."""
        limit = PUBLIC_TEXT_LIMITS[field]
        if len(value or "") > limit:
            raise serializers.ValidationError(f"Tối đa {limit} ký tự.")
        error = public_text_error(value)
        if error:
            raise serializers.ValidationError(error)
        return value

    def validate_short_note(self, value):
        return self._validate_public_text("short_note", value)

    def validate_spec(self, value):
        return self._validate_public_text("spec", value)

    def validate_storage(self, value):
        return self._validate_public_text("storage", value)

    def validate_origin(self, value):
        return self._validate_public_text("origin", value)

    def validate_description(self, value):
        return self._validate_public_text("description", value)

    def get_fields(self):
        fields = super().get_fields()
        if not can_view_item_price(self.context.get("request")):
            fields.pop("current_price", None)  # T9: người không có quyền xem giá không thấy field này
        return fields

    def get_current_price(self, obj):
        """{"rate","valid_from","valid_upto"} của giá đang hiệu lực, hoặc null (BR-DM-02). Không có giá vốn."""
        prefetched = getattr(obj, CURRENT_PRICES_ATTR, None)
        if prefetched is not None:
            price = prefetched[0] if prefetched else None
        else:  # bản ghi vừa tạo/sửa, không qua queryset danh sách
            price = current_item_price(obj)
        if price is None:
            return None
        # Chuỗi ISO, không phải đối tượng date: đường lệnh AI dùng `serializer.data` rồi json.dumps thẳng.
        return {
            "rate": f"{price.rate:.2f}",
            "valid_from": price.valid_from.isoformat(),
            "valid_upto": price.valid_upto.isoformat() if price.valid_upto else None,
        }

    def get_image(self, obj):
        return serialize_item_image(getattr(obj, "image", None), include_uploaded_by=False)
