"""Serializer kho, sổ nhập xuất, phiếu điều chỉnh kho. Không có field tiền / giá vốn (chỉ kg, nhãn, tên)."""
from decimal import Decimal

from django.db.models import Count, Q, Sum
from rest_framework import serializers

from apps.inventory.models import StockEntry, StockLedgerEntry, Warehouse

from .references import ReferenceLookup, describe

SYSTEM_ACTOR_NAME = "Hệ thống"
ZERO = Decimal("0")


def user_display_name(user):
    """Tên hiển thị của người làm: tên trong hồ sơ nhân viên, không có thì tên đăng nhập. Không bao giờ trả SĐT."""
    if user is None:
        return None
    profile = getattr(user, "staff_profile", None)
    return (profile.display_name if profile else "") or user.get_username()


class WarehouseSerializer(serializers.ModelSerializer):
    """`active_batch_count` / `total_qty`: số lô và tổng kg của các lô còn tồn (`qty_available > 0`) trong kho."""

    is_group_label = serializers.SerializerMethodField()
    active_batch_count = serializers.SerializerMethodField()
    total_qty = serializers.SerializerMethodField()

    class Meta:
        model = Warehouse
        fields = ["id", "name", "is_group", "is_group_label", "active_batch_count", "total_qty"]
        read_only_fields = ["id", "is_group_label", "active_batch_count", "total_qty"]

    def get_is_group_label(self, obj):
        return "Nhóm kho" if obj.is_group else "Kho"

    def _stock(self, obj):
        """Danh sách đã `annotate` sẵn; kho vừa tạo (POST) chưa có thì tính một lần."""
        if hasattr(obj, "active_batch_count"):
            return obj.active_batch_count, obj.total_qty
        found = obj.batches.filter(qty_available__gt=0).aggregate(n=Count("pk"), kg=Sum("qty_available"))
        return found["n"], found["kg"]

    def get_active_batch_count(self, obj):
        return self._stock(obj)[0] or 0

    def get_total_qty(self, obj):
        kg = self._stock(obj)[1] or ZERO
        return f"{Decimal(kg):.3f}"


def annotate_warehouse_stock(queryset):
    """Thêm `active_batch_count`, `total_qty` bằng một truy vấn (một JOIN, hai aggregate có điều kiện)."""
    in_stock = Q(batches__qty_available__gt=0)
    return queryset.annotate(
        active_batch_count=Count("batches", filter=in_stock),
        total_qty=Sum("batches__qty_available", filter=in_stock),
    )


class WarehouseCreateInput(serializers.Serializer):
    """Body POST kho. Kiểm tên (trống, trùng) ở `warehouse_services.create_warehouse`, để trả `{detail, code}`."""

    name = serializers.CharField(allow_blank=True, trim_whitespace=False)
    is_group = serializers.BooleanField(required=False, default=False)


class StockLedgerEntrySerializer(serializers.ModelSerializer):
    """
    Một dòng Sổ nhập xuất (R6). `balance_after` do view `annotate` (tổng lũy kế của lô, không đổi theo bộ lọc).
    `reference` giữ nguyên chuỗi gốc để FE cũ không vỡ; FE mới dùng `reference_display` + `reference_link`.
    """

    batch_code = serializers.CharField(source="batch.batch_id", read_only=True)
    item = serializers.IntegerField(source="batch.item_id", read_only=True)
    item_name = serializers.CharField(source="batch.item.name", read_only=True)
    warehouse = serializers.IntegerField(source="batch.warehouse_id", read_only=True)
    warehouse_name = serializers.CharField(source="batch.warehouse.name", read_only=True)
    type_label = serializers.SerializerMethodField()
    balance_after = serializers.DecimalField(max_digits=14, decimal_places=3, read_only=True)
    reference_display = serializers.SerializerMethodField()
    reference_link = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = StockLedgerEntry
        fields = [
            "id", "batch", "batch_code", "item", "item_name", "warehouse", "warehouse_name",
            "movement_type", "type_label", "qty_change", "balance_after",
            "reference", "reference_display", "reference_link", "created_at", "created_by", "created_by_name",
        ]
        read_only_fields = fields

    def get_type_label(self, obj):
        return obj.get_movement_type_display()  # một nguồn nhãn từ `choices` (T44)

    def _describe(self, obj):
        lookup = self.context.get("reference_lookup") or ReferenceLookup()
        return describe(obj, lookup)

    def get_reference_display(self, obj):
        return self._describe(obj)[0]

    def get_reference_link(self, obj):
        return self._describe(obj)[1]

    def get_created_by_name(self, obj):
        return user_display_name(obj.created_by) or SYSTEM_ACTOR_NAME


class StockEntrySerializer(serializers.ModelSerializer):
    """
    Phiếu điều chỉnh kho (R7b). Đợt này chỉ đọc (D-1): lưu một dòng, KHÔNG đổi tồn lô và KHÔNG ghi Sổ nhập xuất.
    """

    code = serializers.SerializerMethodField()
    purpose_label = serializers.CharField(source="get_purpose_display", read_only=True)
    batch_code = serializers.CharField(source="batch.batch_id", read_only=True)
    item_name = serializers.CharField(source="batch.item.name", read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = StockEntry
        fields = [
            "id", "code", "purpose", "purpose_label", "batch", "batch_code", "item_name",
            "qty_change", "reason", "created_by", "created_by_name", "created_at",
        ]
        read_only_fields = ["code", "created_by", "created_at"]  # BR-PQ-16

    def get_code(self, obj):
        return f"SE-{obj.pk}"

    def get_created_by_name(self, obj):
        return user_display_name(obj.created_by)
