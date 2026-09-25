"""
Ghi AuditLog — dùng chung cho mọi service (BR-PQ-04/05).

Append-only. Gọi ở mọi hành động Tầng 2 (duyệt/chốt/huỷ/xác nhận) và mọi thay đổi
`Batch.landed_unit_cost` + chuyển trạng thái `Refund`.
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


def record_audit(action, *, actor=None, obj=None, changes=None, note=""):
    """
    Ghi một dòng AuditLog.

    action  : codename hành động (vd 'confirm_refund', 'close_batch').
    actor   : User hoặc None (= Hệ thống, BR-PQ-07).
    obj     : instance chứng từ liên quan (điền model_name/object_id/object_repr).
    changes : dict {field: {"from": x, "to": y}} — giá trị trước→sau.
    """
    from apps.accounts.models import AuditLog

    kwargs = {
        "actor": actor,
        "action": action,
        "changes": _json_safe(changes or {}),
        "note": note,
    }
    if obj is not None:
        kwargs["model_name"] = obj._meta.label
        kwargs["object_id"] = str(getattr(obj, "pk", "") or "")
        kwargs["object_repr"] = str(obj)[:255]
    return AuditLog.objects.create(**kwargs)
