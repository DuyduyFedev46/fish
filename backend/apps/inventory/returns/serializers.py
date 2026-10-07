"""
Serializer hàng hoàn về kho (R9, 02b §3.8) — status/decision/người tạo/người duyệt/giờ chỉ đọc (BR-PQ-14/16).

Field khai tường minh, không có tiền hay giá vốn (chỉ kg). `delivery_note` và `batch` chỉ nhận id: khi tạo, phiếu giao
phải nằm trong phạm vi của người gọi, ngoài phạm vi hay không tồn tại đều là 404 như nhau (BR-PQ-12). `note` là chữ tự do
(có thể chứa dữ liệu cá nhân): chỉ hiện ở API này, không vào AuditLog, dòng thời gian, AI (bất biến 9).
"""
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from rest_framework import serializers

from apps.common.params import parse_positive_id
from apps.delivery.models import DeliveryNote
from apps.accounts.staff.services import actor_is_owner
from apps.inventory.models import Batch, ReturnToStock
from apps.inventory.returns.services import can_delete_return
from apps.inventory.stock.serializers import user_display_name

from apps.common.pii import has_long_digit_run

from .scope import scope_delivery_notes_for

NOT_FOUND_MESSAGE = "Không tìm thấy phiếu giao."
MAX_NOTE_LENGTH = 500


class _IdField(serializers.PrimaryKeyRelatedField):
    """Id nguyên dương ASCII, không quá int64 (`parse_positive_id`); sai kiểu/ngoài khoảng là 400, không phải 500."""

    def _parse(self, data):
        if isinstance(data, bool) or not isinstance(data, (int, str)):
            self.fail("incorrect_type", data_type=type(data).__name__)
        try:
            return parse_positive_id(str(data))
        except ValueError:
            self.fail("incorrect_type", data_type=type(data).__name__)


class BatchIdField(_IdField):
    def to_internal_value(self, data):
        return super().to_internal_value(self._parse(data))


class ScopedDeliveryNoteField(_IdField):
    """Phiếu giao trong phạm vi người gọi (`scope_delivery_notes_for`); không thấy → 404."""

    def get_queryset(self):
        return scope_delivery_notes_for(self.context["request"].user, DeliveryNote.objects.all())

    def to_internal_value(self, data):
        try:
            return self.get_queryset().get(pk=self._parse(data))
        except ObjectDoesNotExist:
            raise Http404(NOT_FOUND_MESSAGE) from None


class ReturnToStockSerializer(serializers.ModelSerializer):
    code = serializers.SerializerMethodField()
    delivery_note = ScopedDeliveryNoteField()
    delivery_note_code = serializers.CharField(source="delivery_note.code", read_only=True, default=None)
    order_code = serializers.CharField(source="delivery_note.sales_invoice.sales_order.code", read_only=True, default=None)
    batch = BatchIdField(queryset=Batch.objects.all())
    batch_code = serializers.CharField(source="batch.batch_id", read_only=True)
    item_name = serializers.CharField(source="batch.item.name", read_only=True)
    outside_minutes = serializers.SerializerMethodField()
    decision_label = serializers.SerializerMethodField()
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    created_by_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()
    available_actions = serializers.SerializerMethodField()

    class Meta:
        model = ReturnToStock
        fields = [
            "id", "code", "delivery_note", "delivery_note_code", "order_code", "batch", "batch_code", "item_name",
            "qty", "left_warehouse_at", "returned_at", "outside_minutes", "decision", "decision_label",
            "status", "status_label", "created_by", "created_by_name", "approved_by", "approved_by_name",
            "created_at", "note", "available_actions",
        ]
        read_only_fields = [
            "left_warehouse_at", "returned_at", "decision", "status", "created_by", "approved_by", "created_at",
        ]  # BR-PQ-14/16
        extra_kwargs = {"note": {"max_length": MAX_NOTE_LENGTH}}

    def validate_note(self, value):
        # Bất biến 9: ghi chú tự do không chứa số điện thoại/số tài khoản — cùng luật với các ghi chú khác (QA Lô 9 B1).
        if has_long_digit_run(value or ""):
            raise serializers.ValidationError("Ghi chú không được chứa dãy số dài (số điện thoại, số tài khoản).")
        return value

    def get_code(self, obj):
        return f"RT-{obj.pk}"

    def get_outside_minutes(self, obj):
        """Số phút hàng ở ngoài kho = giờ về − giờ rời kho; None khi thiếu một trong hai mốc."""
        if obj.left_warehouse_at is None or obj.returned_at is None:
            return None
        return max(0, int((obj.returned_at - obj.left_warehouse_at).total_seconds() // 60))

    def get_decision_label(self, obj):
        return obj.get_decision_display()  # nhãn một nguồn từ `choices` (T45)

    def get_created_by_name(self, obj):
        return user_display_name(obj.created_by)

    def get_approved_by_name(self, obj):
        return user_display_name(obj.approved_by)

    def get_available_actions(self, obj):
        """Thao tác `user` làm được trên phiếu ở trạng thái hiện tại: `approve`, `cancel`, `delete` (xoá mềm, chỉ Chủ).
        Kết quả "chủ" tính một lần mỗi request (danh sách 20 dòng không thêm truy vấn)."""
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return []
        actions = []
        if obj.status == ReturnToStock.Status.DRAFT:
            if user.has_perm("inventory.approve_returntostock"):
                actions.append("approve")
            is_creator = obj.created_by_id == user.pk and user.has_perm("inventory.add_returntostock")
            if is_creator or user.has_perm("inventory.approve_returntostock") or user.has_perm("inventory.change_returntostock"):
                actions.append("cancel")
        # TL8F-L3: khớp API (`soft_delete` đòi `add_returntostock`), để FE không hiện nút rồi nhận 403.
        if can_delete_return(obj) and self._is_owner(user) and user.has_perm("inventory.add_returntostock"):
            actions.append("delete")
        return actions

    def _is_owner(self, user):
        cached = self.context.get("_is_owner")
        if cached is None:
            cached = self.context["_is_owner"] = actor_is_owner(user)
        return cached
