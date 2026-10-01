"""
Định nghĩa CommandSpec cho lệnh AI tự sinh (02b §2.3, DW-07).
"""
from dataclasses import dataclass, field
from typing import Any

from apps.ai import command_groups


@dataclass
class CommandSpec:
    id: str
    title: str
    description: str = ""
    kind: str = "read"                      # "read" | "write"
    group: str = command_groups.PURCHASING  # command_groups: PURCHASING | SALES | CUSTOMER_SERVICE
    screens: tuple = ()
    keywords: list[str] = field(default_factory=list)
    method: str = "GET"
    path: str = ""
    action: str = ""
    detail: bool = False
    target: str | None = None               # "detail" | None
    view_cls: Any = None
    required_perms: tuple = ()              # Quyền Tầng 2
    sensitivity: str = command_groups.SENSITIVITY_HIGH  # command_groups.SENSITIVITY_*: HIGH | MEDIUM | LOW
    channel: str = "local"                  # "local" | "cloud"
    max_level: str = "C"                    # "A" | "B" | "C"
    undo: str = ""                          # "cancel_action:<act>" | "defer" | ""
    undo_missing: bool = False              # True nếu undo trỏ tới action chưa có
    red_zone: bool = False
    limits: dict = field(default_factory=dict)  # khai báo ngưỡng của AiMeta: {"<field>": "kg"|"vnd"}
    force_c: bool = False
    form_only: bool = False
    is_forbidden: bool = False
    input_serializer_cls: Any = None
    input_schema: dict | None = None
    schema_tokens_est: int = 0
    all_output_fields: list[str] = field(default_factory=list)
