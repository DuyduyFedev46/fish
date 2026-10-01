"""
Guidance "chỉ dòng thời gian" cho phiếu giao (`delivery`) — Lô 2, R2 (02b §3.8).

Quyền và phạm vi giống `DeliveryNoteViewSet`: cần `delivery.view_deliverynote`; người không có full scope
(NV giao) chỉ xem phiếu gán cho mình. Nhãn dòng không chứa tên, SĐT, địa chỉ, ghi chú hay lý do thất bại tự do
của khách (bất biến 9); response gắn `Cache-Control: no-store`.
"""
from apps.common.api import has_full_delivery_scope
from apps.common.guidance.api import register_guidance
from apps.common.guidance.audit_timeline import make_audit_timeline_provider

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


def _scope_notes_for(user, qs):
    """Giống `DeliveryNoteViewSet.get_queryset`: NV giao chỉ thấy phiếu gán cho mình."""
    if has_full_delivery_scope(user):
        return qs
    return qs.filter(assigned_to=user)


register_guidance(
    "delivery",
    make_audit_timeline_provider(
        DeliveryNote,
        "delivery.view_deliverynote",
        _scope_notes_for,
        doc_type="delivery",
        code_fn=lambda n: n.code,
        action_labels=ACTION_LABELS,
        created_label="Hệ thống tạo phiếu giao",
        no_store=True,
    ),
)
