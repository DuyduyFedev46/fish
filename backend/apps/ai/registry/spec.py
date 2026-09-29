"""
Định nghĩa CommandSpec cho lệnh AI tự sinh (02b §2.3, DW-07).
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CommandSpec:
    id: str
    title: str
    description: str = ""
    kind: str = "read"                      # "read" | "write"
    group: str = "thu_mua"                  # thu_mua | ban_hang | cskh
    screens: tuple = ()
    keywords: list[str] = field(default_factory=list)
    method: str = "GET"
    path: str = ""
    action: str = ""
    detail: bool = False
    target: str | None = None               # "detail" | None
    view_cls: Any = None
    required_perms: tuple = ()              # Quyền Tầng 2
    sensitivity: str = "cao"                # "cao" | "trung_binh" | "thap"
    channel: str = "local"                  # "local" | "cloud"
    max_level: str = "C"                    # "A" | "B" | "C"
    undo: str = ""                          # "cancel_action:<act>" | "defer" | ""
    undo_missing: bool = False              # True nếu undo trỏ tới action chưa có
    red_zone: bool = False
    force_c: bool = False
    form_only: bool = False
    is_forbidden: bool = False
    input_serializer_cls: Any = None
    input_schema: dict | None = None
    schema_tokens_est: int = 0
    all_output_fields: list[str] = field(default_factory=list)
