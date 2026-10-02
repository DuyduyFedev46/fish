"""
Serializer phiếu kiểm kê (R8) + đầu vào dòng số đếm (B1) — 02b §3 B1.

Không có field tiền nào: tồn và chênh lệch chỉ tính bằng kg, nên không có giá vốn để ẩn (bất biến 1).
Không có dữ liệu khách (bất biến 9): chỉ có tên hiển thị của NHÂN VIÊN.
"""
from decimal import Decimal

from rest_framework import serializers

from apps.common.exceptions import BusinessError
from apps.common.params import parse_positive_id
from apps.inventory.models import StockReconciliation

from .services import MAX_LINES, RECON_LINE_INVALID, SYSTEM_NAME, staff_name

ZERO = Decimal("0")
QTY_QUANT = Decimal("0.001")


def _user_ref(user):
    return None if user is None else {"id": user.pk, "display_name": staff_name(user)}


def _qty(value):
    return format(Decimal(value).quantize(QTY_QUANT), "f")


class PositiveIdField(serializers.Field):
    """Id nguyên dương cho khoá ngoại trong body: số nguyên hoặc chuỗi chữ số ASCII, không quá int64."""

    default_error_messages = {"invalid": "Chọn một lô hợp lệ."}

    def to_internal_value(self, data):
        if isinstance(data, bool):
            self.fail("invalid")
        try:
            return parse_positive_id(str(data) if isinstance(data, int) else data)
        except ValueError:
            self.fail("invalid")

    def to_representation(self, value):
        return value


class ReconciliationLineInput(serializers.Serializer):
    """Một dòng số đếm client gửi: lô, số đếm, lý do. `system_qty`/`difference_qty` nếu có sẽ bị bỏ qua."""

    batch = PositiveIdField()
    counted_qty = serializers.DecimalField(
        max_digits=12, decimal_places=3,
        error_messages={"invalid": "Số đếm phải là số kg, tối đa 3 chữ số thập phân."},
    )
    reason = serializers.CharField(
        required=False, allow_blank=True, trim_whitespace=False,
        error_messages={"invalid": "Lý do không hợp lệ."},
    )  # độ dài tối đa kiểm ở service (MAX_REASON_LENGTH)


def _first_message(errors):
    for messages in errors.values():
        first = messages[0] if isinstance(messages, (list, tuple)) and messages else messages
        return str(first)
    return "Dòng không hợp lệ."


def parse_line_inputs(raw):
    """
    Đổi danh sách dòng thô trong body thành list `{batch, counted_qty, reason}` đã đúng kiểu.
    Sai kiểu/định dạng → `BusinessError` mã `RECON_LINE_INVALID`, thông điệp tiếng Việt không chép lại giá trị gửi lên,
    kèm `line_index` (từ 0) để FE tô đúng dòng. Kiểm nghiệp vụ (âm, trùng lô, lô đã chốt…) làm ở service.
    """
    if not isinstance(raw, list) or not raw:
        raise BusinessError("Cần ít nhất một dòng số đếm.", code=RECON_LINE_INVALID)
    if len(raw) > MAX_LINES:
        raise BusinessError(f"Tối đa {MAX_LINES} dòng mỗi phiếu.", code=RECON_LINE_INVALID)
    parsed = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise BusinessError(
                f"Dòng {index + 1}: dữ liệu dòng không hợp lệ.", code=RECON_LINE_INVALID, extra={"line_index": index},
            )
        serializer = ReconciliationLineInput(data=item)
        if not serializer.is_valid():
            raise BusinessError(
                f"Dòng {index + 1}: {_first_message(serializer.errors)}",
                code=RECON_LINE_INVALID, extra={"line_index": index},
            )
        parsed.append(dict(serializer.validated_data))
    return parsed


class StockReconciliationLineSerializer(serializers.Serializer):
    """Dòng kiểm kê chỉ đọc: lô, mặt hàng, kho và số liệu kg."""

    id = serializers.IntegerField(read_only=True)
    batch = serializers.IntegerField(source="batch_id", read_only=True)
    batch_code = serializers.CharField(source="batch.batch_id", read_only=True)
    item_name = serializers.CharField(source="batch.item.name", read_only=True)
    warehouse_name = serializers.CharField(source="batch.warehouse.name", read_only=True)
    system_qty = serializers.DecimalField(max_digits=12, decimal_places=3, read_only=True)
    counted_qty = serializers.DecimalField(max_digits=12, decimal_places=3, read_only=True)
    difference_qty = serializers.DecimalField(max_digits=12, decimal_places=3, read_only=True)
    reason = serializers.CharField(read_only=True)


class StockReconciliationSerializer(serializers.ModelSerializer):
    """Danh sách + đầu vào tạo/sửa phiếu (chỉ `count_date`, `note` ghi được)."""

    code = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()
    approved_by = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()
    warehouse_names = serializers.SerializerMethodField()
    line_count = serializers.SerializerMethodField()
    short_count = serializers.SerializerMethodField()
    over_count = serializers.SerializerMethodField()
    match_count = serializers.SerializerMethodField()
    short_qty = serializers.SerializerMethodField()
    over_qty = serializers.SerializerMethodField()
    net_difference = serializers.SerializerMethodField()
    available_actions = serializers.SerializerMethodField()
    approve_blocked_reason = serializers.SerializerMethodField()

    class Meta:
        model = StockReconciliation
        fields = [
            "id", "code", "count_date", "status", "status_label", "note", "created_by", "approved_by",
            "approved_at", "updated_at", "updated_by_name", "warehouse_names", "line_count", "short_count",
            "over_count", "match_count", "short_qty", "over_qty", "net_difference", "available_actions",
            "approve_blocked_reason",
        ]
        read_only_fields = [  # BR-PQ-14/16: chỉ count_date, note ghi được
            "status", "created_by", "approved_by", "approved_at", "updated_at",
        ]

    def _lines(self, obj):
        return list(obj.lines.all())

    def _summary(self, obj):
        cached = getattr(obj, "_line_summary", None)
        if cached is None:
            lines = self._lines(obj)
            diffs = [row.difference_qty for row in lines]
            cached = {
                "warehouse_names": sorted({row.batch.warehouse.name for row in lines}),
                "line_count": len(lines),
                "short_count": sum(1 for d in diffs if d < ZERO),
                "over_count": sum(1 for d in diffs if d > ZERO),
                "match_count": sum(1 for d in diffs if d == ZERO),
                "short_qty": _qty(-sum((d for d in diffs if d < ZERO), ZERO)),
                "over_qty": _qty(sum((d for d in diffs if d > ZERO), ZERO)),
                "net_difference": _qty(sum(diffs, ZERO)),
            }
            obj._line_summary = cached
        return cached

    def get_code(self, obj):
        return f"KK-{obj.pk}"

    def get_status_label(self, obj):
        return obj.get_status_display()

    def get_created_by(self, obj):
        return _user_ref(obj.created_by)

    def get_approved_by(self, obj):
        return _user_ref(obj.approved_by)

    def get_updated_by_name(self, obj):
        kind = getattr(obj, "last_actor_kind", None)
        if kind is None:  # phiếu cũ chưa có dòng nhật ký (hoặc đối tượng chưa qua queries)
            return staff_name(obj.created_by)
        if kind == "ai":
            return f"AI của {obj.last_ai_actor_display_name or obj.last_ai_actor_username or SYSTEM_NAME}"
        if kind == "system" or obj.last_actor_username is None:
            return SYSTEM_NAME
        return obj.last_actor_display_name or obj.last_actor_username

    def get_warehouse_names(self, obj):
        return self._summary(obj)["warehouse_names"]

    def get_line_count(self, obj):
        return self._summary(obj)["line_count"]

    def get_short_count(self, obj):
        return self._summary(obj)["short_count"]

    def get_over_count(self, obj):
        return self._summary(obj)["over_count"]

    def get_match_count(self, obj):
        return self._summary(obj)["match_count"]

    def get_short_qty(self, obj):
        return self._summary(obj)["short_qty"]

    def get_over_qty(self, obj):
        return self._summary(obj)["over_qty"]

    def get_net_difference(self, obj):
        return self._summary(obj)["net_difference"]

    def get_available_actions(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user is None or obj.status == StockReconciliation.Status.APPROVED:
            return []
        can_change = user.has_perm("inventory.change_stockreconciliation")
        actions = []
        if obj.status == StockReconciliation.Status.DRAFT:
            if can_change:
                actions += ["edit_lines", "submit"]
        elif obj.status == StockReconciliation.Status.SUBMITTED:
            if can_change:
                actions.append("return_to_draft")
            if user.has_perm("inventory.approve_stockreconciliation"):
                actions.append("approve")
        return actions

    def get_approve_blocked_reason(self, obj):
        """Luôn None: BR-KK-02/BR-KK-08 đã bỏ (Duy chốt 02/10, #6), không còn lý do nào chặn người có quyền duyệt."""
        return None


class StockReconciliationDetailSerializer(StockReconciliationSerializer):
    """Chi tiết: thêm `lines` (kèm chênh lệch)."""

    lines = serializers.SerializerMethodField()

    class Meta(StockReconciliationSerializer.Meta):
        fields = [*StockReconciliationSerializer.Meta.fields, "lines"]

    def get_lines(self, obj):
        return StockReconciliationLineSerializer(self._lines(obj), many=True, context=self.context).data
