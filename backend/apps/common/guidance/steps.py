"""
Các cấu trúc dữ liệu cho khối Tiếp theo · Đã làm (Guidance).
"""
from dataclasses import dataclass, field
from typing import Any, Optional

from django.conf import settings


@dataclass(frozen=True)
class Missing:
    code: str
    text: str


@dataclass(frozen=True)
class Why:
    br: str
    text: str


@dataclass(frozen=True)
class NextStep:
    key: str
    label: str
    actor: str  # "user" | "system"
    allowed: bool
    who: list[str] = field(default_factory=list)
    missing: list[Missing] = field(default_factory=list)
    deadline: Optional[str] = None
    why: Optional[Why] = None
    command: Optional[str] = None
    ai: Optional[dict[str, Any]] = None


def resolve_step_ai(step: NextStep, user: Any = None) -> Optional[dict[str, Any]]:
    """
    Tính toán thông tin trường `ai` trên NextStep dựa trên effective_level của lệnh (DW-14).
    - AI_ENABLED=False -> trả về None (DW-14-AC8)
    - Không có command hoặc user chưa xác thực -> trả về None
    - Lấy spec từ CommandRegistry và tính effective_level(user, spec)
    - level in ("OFF", None) -> trả về None
    - level C -> 'AI soạn nháp <label>'
    - level B -> 'AI thực thi <label>'
    - level A -> 'AI tra cứu <label>'
    """
    if not getattr(settings, "AI_ENABLED", False):
        return None
    if not step.command:
        return None
    if not user or not getattr(user, "is_authenticated", False):
        return None

    try:
        from apps.ai.policy.effective import effective_level
        from apps.ai.registry.discovery import get_registry

        registry = get_registry()
        spec = registry.get(step.command)
        if not spec:
            return None

        level = effective_level(user, spec)
        if level in ("OFF", None):
            return None

        label = None
        action_text = step.label.lower()
        if level == "C":
            label = f"AI soạn nháp {action_text}"
        elif level == "B":
            label = f"AI thực thi {action_text}"
        elif level == "A":
            label = f"AI tra cứu {action_text}"

        if not label:
            return None

        return {"level": level, "label": label}
    except Exception:
        return None


def step_to_dict(step: NextStep, user: Any = None) -> dict[str, Any]:
    ai_val = step.ai if step.ai is not None else resolve_step_ai(step, user)
    return {
        "key": step.key,
        "label": step.label,
        "actor": step.actor,
        "allowed": step.allowed,
        "who": list(step.who),
        "missing": [{"code": m.code, "text": m.text} for m in step.missing],
        "deadline": step.deadline,
        "why": {"br": step.why.br, "text": step.why.text} if step.why else None,
        "command": step.command,
        "ai": ai_val,
    }
