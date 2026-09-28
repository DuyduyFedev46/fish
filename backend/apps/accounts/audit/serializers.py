"""
Serialize dòng AuditLog cho endpoint nhật ký (contract 02b mục 3 — S03).

`actor_display`: dòng AI → `ai:<tên user>` (từ `ai_actor`); dòng người → username;
dòng hệ thống → `system`. `changes`/`note` trả nguyên văn — quy ước ghi log (BR-AI-09,
bất biến 9): chỉ chứa mã chứng từ/mã lệnh/mã đề xuất, không bao giờ tên/SĐT/địa chỉ khách.
"""


def audit_item(row) -> dict:
    if row.actor_kind == "ai":
        actor_display = f"ai:{row.ai_actor.get_username()}" if row.ai_actor else "ai:?"
    elif row.actor is not None:
        actor_display = row.actor.get_username()
    else:
        actor_display = "system"
    return {
        "id": row.pk,
        "actor_kind": row.actor_kind,
        "actor_display": actor_display,
        "ai_actor": row.ai_actor_id,
        "action": row.action,
        "model_name": row.model_name,
        "object_id": row.object_id,
        "object_repr": row.object_repr,
        "changes": row.changes,
        "note": row.note,
        "proposal_ref": row.proposal_ref,
        "created_at": row.created_at,
    }
