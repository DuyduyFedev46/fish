"""
Định dạng dòng thời gian cho khối Guidance (02b §6.7, Q-M16).

Bất biến:
- Không rò giá vốn với người xem thiếu view_costprice.
- Không rò PII (tên, SĐT, địa chỉ, nội dung CK).
- Không đưa `changes` thô.
- Sửa L-4: dòng `actor_kind=ai` hiện "AI của <tên hiển thị>" kèm mức, không hiện "Hệ thống".
- Trường `config_version` chỉ xuất hiện khi người xem có `ai.manage_ai_policy`.
"""
from typing import Any


def format_guidance_timeline(events: list[Any], viewer=None) -> list[dict[str, Any]]:
    """
    Chuyển danh sách TimelineEvent thành cấu trúc JSON contract 02b §6.7.
    """
    can_manage_policy = viewer.has_perm("ai.manage_ai_policy") if viewer else False
    result = []
    for e in events:
        actor_kind = getattr(e, "actor_kind", "system")
        actor_dict: dict[str, Any] = {
            "kind": actor_kind,
            "display": getattr(e, "actor_display", "Hệ thống"),
        }
        if actor_kind == "ai":
            actor_dict["level"] = getattr(e, "ai_level", None) or "C"
            cfg_ver = getattr(e, "ai_config_version", None)
            if can_manage_policy and cfg_ver is not None:
                actor_dict["config_version"] = cfg_ver

        at_val = e.at.isoformat() if hasattr(e.at, "isoformat") else str(e.at)
        result.append({
            "at": at_val,
            "kind": e.kind,
            "label": e.label,
            "doc": getattr(e, "doc", "order"),
            "actor": actor_dict,
        })
    return result
