"""
Ghi AuditLog — dùng chung cho mọi service (BR-PQ-04/05).

Append-only. Gọi ở mọi hành động Tầng 2 (duyệt/chốt/huỷ/xác nhận) và mọi thay đổi
`Batch.landed_unit_cost` + chuyển trạng thái `Refund`.

Quy ước: không đưa số giá vốn vào `note`; không chép chữ người dùng tự gõ (dùng `note_marker`). Xem COST_KEYS trong apps.common.cost_keys.
"""
from contextlib import contextmanager
import contextvars
from dataclasses import dataclass
import datetime
from decimal import Decimal
from typing import Optional


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


NOTE_PRESENT_LABEL = "Có ghi chú (xem trên chứng từ gốc)"


def note_marker(text):
    """
    Nhãn cố định thay cho chữ người dùng tự gõ (TL-D3-L4, bất biến 9).

    Chữ tự do có thể chứa tên/SĐT của khách hay người chuyển khoản, nên KHÔNG chép vào
    `AuditLog.note`/`changes`. Ghi chú vẫn nằm trên chứng từ gốc (có phân quyền riêng);
    Nhật ký chỉ biết "có ghi chú hay không". Trả "" khi không có chữ.
    """
    return NOTE_PRESENT_LABEL if str(text or "").strip() else ""


VALID_ACTOR_KINDS = ("user", "system", "ai")


@dataclass
class AiAuditScope:
    ai_actor: Optional[object] = None
    level: str = ""
    config_version: Optional[int] = None
    policy_version: Optional[int] = None
    action_ref: str = ""
    is_proposal: bool = False


ai_audit_scope: contextvars.ContextVar[Optional[AiAuditScope]] = contextvars.ContextVar(
    "ai_audit_scope", default=None
)


@contextmanager
def set_ai_audit_scope(
    ai_actor=None,
    level="",
    config_version=None,
    policy_version=None,
    action_ref="",
    is_proposal=False,
):
    """
    Context manager thiết lập ngữ cảnh AI audit cho lệnh đang thực thi (02b §4.4).
    Tự động reset token trong finally để không dính sang request UI kế tiếp cùng thread.
    """
    scope = AiAuditScope(
        ai_actor=ai_actor,
        level=level,
        config_version=config_version,
        policy_version=policy_version,
        action_ref=action_ref,
        is_proposal=is_proposal,
    )
    token = ai_audit_scope.set(scope)
    try:
        yield scope
    finally:
        ai_audit_scope.reset(token)


def record_audit(action, *, actor=None, obj=None, changes=None, note="",
                 actor_kind="user", ai_actor=None, proposal_ref="",
                 ai_level="", ai_config_version=None, ai_policy_version=None, **kwargs):
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

    scope = ai_audit_scope.get()
    if scope:
        if not proposal_ref and scope.action_ref:
            proposal_ref = scope.action_ref
        if not ai_level and scope.level:
            ai_level = scope.level
        if ai_config_version is None and scope.config_version is not None:
            ai_config_version = scope.config_version
        if ai_policy_version is None and scope.policy_version is not None:
            ai_policy_version = scope.policy_version

        if scope.is_proposal:
            actor_kind = "ai"
            ai_actor = ai_actor or scope.ai_actor
        elif scope.ai_actor and actor_kind == "user" and actor is None:
            actor_kind = "ai"
            ai_actor = ai_actor or scope.ai_actor

    if actor_kind not in VALID_ACTOR_KINDS:
        raise ValueError(f"actor_kind không hợp lệ: {actor_kind!r}")
    if actor_kind == "ai":
        ai_actor = ai_actor or actor
        actor = None  # dòng AI không gán actor user (BR-PQ-07)
    elif actor is None:
        actor_kind = "system"

    log_kwargs = {
        "actor": actor,
        "action": action,
        "changes": _json_safe(changes or {}),
        "note": note,
        "actor_kind": actor_kind,
        "ai_actor": ai_actor,
        "proposal_ref": proposal_ref or "",
        "ai_level": ai_level or "",
        "ai_config_version": ai_config_version,
        "ai_policy_version": ai_policy_version,
    }
    if obj is not None:
        log_kwargs["model_name"] = obj._meta.label
        log_kwargs["object_id"] = str(getattr(obj, "pk", "") or "")
        log_kwargs["object_repr"] = str(obj)[:255]
    return AuditLog.objects.create(**log_kwargs)
