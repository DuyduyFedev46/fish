"""
Serialize dòng AuditLog cho endpoint nhật ký (contract 02b mục 3 — S03, S01).

`actor_display`: dòng AI → `ai:<tên user>` (từ `ai_actor`); dòng người → username;
dòng hệ thống → `system`. `changes` trả nguyên văn (quy ước ghi log BR-AI-09, bất biến 9: chỉ mã chứng từ/mã lệnh/mã đề xuất).
`note` của dòng cũ có thể còn chữ tự do nên qua `safe_note` khi hiển thị.
Lọc bỏ các khoá giá vốn trong `changes` nếu user không có quyền xem giá vốn (S01, BR-PQ-13).
"""
import re

from django.conf import settings
from django.db.models import Q

from apps.common.audit import NOTE_PRESENT_LABEL, NOTE_PRESENT_NEUTRAL_LABEL
from apps.common.cost_keys import redact_cost

_FIXED_NOTES = ("", NOTE_PRESENT_LABEL, NOTE_PRESENT_NEUTRAL_LABEL)
# Action từng ghi chữ người dùng gõ vào `note` (TL-D3-L4). Dòng cũ có thể còn tên/SĐT: chỉ trả `note`
# khi khớp mẫu cố định do hệ thống sinh, không thì trả nhãn trung tính. Không sửa DB (bất biến 4).
_GUARDED_ACTIONS = {
    "attach_payment": (),
    "resolve_payment": (re.compile(r"Hoàn tiền theo phiếu hoàn #\d+"),),
    "mark_refund_failed": (),
    "cancel_paid_order": (),  # xử lý riêng: nhãn lý do + nhãn ghi chú
    "delivery_unconfirmed": (),
    "delivery_confirm_skipped": (),
    "delivery_extended": (),
}
_REJECT_NOTE = re.compile(r"Từ chối đề xuất AI [\w-]+")


def _cancel_note_ok(note):
    from apps.sales.orders.services import CANCEL_REASON_LABELS

    labels = [*CANCEL_REASON_LABELS.values(), "Không rõ"]
    for label in labels:
        base = f"Lý do: {label}"
        if note in (base, f"{base} · {NOTE_PRESENT_LABEL}", f"{base} · {NOTE_PRESENT_NEUTRAL_LABEL}"):
            return True
    return False


def safe_note(action, note):
    """`note` an toàn để hiển thị: khớp mẫu cố định thì giữ, không thì "Có ghi chú"."""
    if note in _FIXED_NOTES:
        return note
    if action.startswith("reject_"):
        return note if _REJECT_NOTE.fullmatch(note) else NOTE_PRESENT_NEUTRAL_LABEL
    if action not in _GUARDED_ACTIONS:
        return note
    if action == "cancel_paid_order":
        return note if _cancel_note_ok(note) else NOTE_PRESENT_NEUTRAL_LABEL
    if any(p.fullmatch(note) for p in _GUARDED_ACTIONS[action]):
        return note
    return NOTE_PRESENT_NEUTRAL_LABEL


def exclude_ai_rows(qs):
    """
    Khi AI tắt (`AI_ENABLED=False`) ẩn các dòng DO AI làm: `actor_kind="ai"` và dòng Hệ thống thuộc vòng đời
    đề xuất AI (`actor_kind="system"` có `proposal_ref`). GIỮ dòng do người làm: duyệt/từ chối đề xuất,
    dòng nghiệp vụ do người duyệt thực thi (tự gắn `proposal_ref`), và `ai_config_*`/`ai_policy_*` do Chủ đổi
    (kiểm toán BR-PQ-04/05).
    """
    if getattr(settings, "AI_ENABLED", False):
        return qs
    return qs.exclude(Q(actor_kind="ai") | (Q(actor_kind="system") & ~Q(proposal_ref="")))


def audit_item(row, *, can_view_cost: bool = True) -> dict:
    if row.actor_kind == "ai":
        actor_display = f"ai:{row.ai_actor.get_username()}" if row.ai_actor else "ai:?"
    elif row.actor is not None:
        actor_display = row.actor.get_username()
    else:
        actor_display = "system"

    changes = row.changes
    if not can_view_cost:
        changes = redact_cost(changes)

    return {
        "id": row.pk,
        "actor_kind": row.actor_kind,
        "actor_display": actor_display,
        "ai_actor": row.ai_actor_id,
        "action": row.action,
        "model_name": row.model_name,
        "object_id": row.object_id,
        "object_repr": row.object_repr,
        "changes": changes,
        "note": safe_note(row.action, row.note),
        "proposal_ref": row.proposal_ref,
        "created_at": row.created_at,
    }
