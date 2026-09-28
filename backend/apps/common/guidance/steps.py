"""
Các cấu trúc dữ liệu cho khối Tiếp theo · Đã làm (Guidance).
"""
from dataclasses import dataclass, field
from typing import Any, Optional


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


def step_to_dict(step: NextStep) -> dict[str, Any]:
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
        "ai": step.ai,
    }
