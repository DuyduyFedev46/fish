"""
Ghi AuditLog — dùng chung cho mọi service (BR-PQ-04/05).

Append-only. Gọi ở mọi hành động Tầng 2 (duyệt/chốt/huỷ/xác nhận) và mọi thay đổi
`Batch.landed_unit_cost` + chuyển trạng thái `Refund`.

Quy ước: không đưa số giá vốn vào `note`. Xem COST_KEYS trong apps.common.cost_keys.
"""
import datetime
from decimal import Decimal


def _json_safe(value):
    """Ép giá trị về dạng JSON-serializable (Decimal/date -> str)."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


VALID_ACTOR_KINDS = ("user", "system", "ai")


def record_audit(action, *, actor=None, obj=None, changes=None, note="",
                 actor_kind="user", ai_actor=None, proposal_ref=""):
    """
    Ghi một dòng AuditLog (append-only, BR-PQ-04/05/06).

    action        : codename hành động (vd 'confirm_refund', 'close_batch').
    actor         : User hoặc None (= Hệ thống, BR-PQ-07).
    obj           : instance chứng từ liên quan (điền model_name/object_id/object_repr).
    changes       : dict {field: {"from": x, "to": y}} — giá trị trước→sau.
    actor_kind    : "user" | "system" | "ai" (S03, BR-AI-08). Dòng AI: actor=None,
                    ai_actor = user bị AI thay mặt — hiển thị `ai:<tên user>`.
    ai_actor      : user mà AI thay mặt (chỉ có nghĩa khi actor_kind="ai").
    proposal_ref  : mã đề xuất (dòng thực thi ghi note mã đề xuất + proposal_ref).

    Chữ ký cũ giữ nguyên tương thích — các call-site hiện có không phải đổi. Quy tắc
    chuẩn hoá khớp backfill migration 0007: actor=None (với actor_kind mặc định) →
    actor_kind="system".
    """
    from apps.accounts.models import AuditLog

    if actor_kind not in VALID_ACTOR_KINDS:
        raise ValueError(f"actor_kind không hợp lệ: {actor_kind!r}")
    if actor_kind == "ai":
        ai_actor = ai_actor or actor
        actor = None  # dòng AI không gán actor user (BR-PQ-07)
    elif actor is None:
        actor_kind = "system"

    kwargs = {
        "actor": actor,
        "action": action,
        "changes": _json_safe(changes or {}),
        "note": note,
        "actor_kind": actor_kind,
        "ai_actor": ai_actor,
        "proposal_ref": proposal_ref or "",
    }
    if obj is not None:
        kwargs["model_name"] = obj._meta.label
        kwargs["object_id"] = str(getattr(obj, "pk", "") or "")
        kwargs["object_repr"] = str(obj)[:255]
    return AuditLog.objects.create(**kwargs)
