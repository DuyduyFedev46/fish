"""
Guidance "chỉ dòng thời gian" cho phiếu giao (`delivery`) — Lô 2, R2 (02b §3.8).

Quyền và phạm vi giống API chi tiết (quyền xem dòng thời gian = quyền xem chi tiết, 02b §3.8 R2):
- Có `delivery.view_deliverynote`: giống `DeliveryNoteViewSet`, theo phạm vi D3 của nhóm (`scope.scope_deliveries_for`,
  PV-04): `assigned` chỉ xem phiếu gán cho mình.
- Chỉ có `delivery.confirm_with_customer` (CSKH, QA5-B2): xem phiếu có mục chờ gọi nằm trong phạm vi gọi xác nhận
  của họ, dùng đúng `note_in_confirmation_scope` (D4, PV-05) của `GET /api/confirmation/queue/<note_id>/`.
  Ngoài phạm vi → 404 như chi tiết.
Nhãn dòng không chứa tên, SĐT, địa chỉ, ghi chú hay lý do thất bại tự do
của khách (bất biến 9); response gắn `Cache-Control: no-store`.
"""
from apps.common.guidance.api import register_guidance
from apps.common.guidance.audit_timeline import make_audit_timeline_provider
from apps.delivery.confirmation.scope import note_in_confirmation_scope
from apps.delivery.scope import scope_deliveries_for

from .models import DeliveryNote


def _advance_label(row) -> str:
    to = ((row.changes or {}).get("status") or {}).get("to")
    try:
        return f"Chuyển trạng thái giao hàng sang {DeliveryNote.Status(to).label}"
    except ValueError:
        return "Chuyển trạng thái giao hàng"


ACTION_LABELS = {
    "delivery_advance_status": _advance_label,
    "delivery_mark_failed": "Báo giao thất bại",
    "delivery_confirmed": "Xác nhận đơn với khách",
    "delivery_call_recorded": "Ghi nhận cuộc gọi xác nhận",
    "delivery_escalated": "Chuyển việc xác nhận lên người có quyền",
    "delivery_unconfirmed": "Bỏ xác nhận đơn",
    "delivery_confirm_skipped": "Bỏ qua bước xác nhận",
    "delivery_extended": "Gia hạn chờ xác nhận",
    "recipient_changed": "Đổi thông tin nhận hàng",
    "label_printed": "In tem giao",
    "label_reprinted": "In lại tem giao",
    "label_voided": "Huỷ tem giao",
}


VIEW_NOTE_PERM = "delivery.view_deliverynote"
CONFIRM_PERM = "delivery.confirm_with_customer"


def _can_view_timeline(user) -> bool:
    return user.has_perm(VIEW_NOTE_PERM) or user.has_perm(CONFIRM_PERM)


def _scope_notes_for(user, qs):
    """Giống `DeliveryNoteViewSet.get_queryset`: cùng hàm phạm vi D3."""
    if not user.has_perm(VIEW_NOTE_PERM):
        # Đường CSKH: API hàng chờ chỉ có phiếu đã có mục chờ gọi; phạm vi từng phiếu kiểm ở `_note_in_scope`.
        return qs.filter(confirmation__isnull=False)
    return scope_deliveries_for(user, qs)


def _note_in_scope(user, note) -> bool:
    """CSKH: đúng hàm phạm vi của API hàng chờ xác nhận. Người có quyền xem phiếu đã lọc ở queryset."""
    if user.has_perm(VIEW_NOTE_PERM):
        return True
    return note_in_confirmation_scope(user, note)


register_guidance(
    "delivery",
    make_audit_timeline_provider(
        DeliveryNote,
        _can_view_timeline,
        _scope_notes_for,
        doc_type="delivery",
        code_fn=lambda n: n.code,
        action_labels=ACTION_LABELS,
        created_label="Hệ thống tạo phiếu giao",
        no_store=True,
        object_scope_fn=_note_in_scope,
    ),
)
