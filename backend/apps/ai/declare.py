"""
Khai báo siêu dữ liệu AI cho ViewSet và action DRF (02b §2.5, DW-07, DW-08).
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AiMeta:
    title: str = ""
    description: str = ""
    group: str = ""
    screens: tuple = ()
    sensitivity: str = ""
    channel: str = ""
    keywords: tuple = ()
    max_level: str = ""                  # "" = theo mặc định (đọc A, ghi C). "B"/"A" cần undo.
    undo: str = ""                       # "cancel_action:<tên action huỷ bằng trạng thái>" | "defer"
    limits: dict = field(default_factory=dict)   # {"<field>": "kg"|"vnd"}
    lookup: str = ""                     # field mã nghiệp vụ cho target (vd "batch_id")


class AiDeclarable:
    """
    Mixin cho mọi ViewSet back-office (thông qua DocumentViewSet hoặc kế thừa trực tiếp).
    Hỗ trợ tự động nhận diện required_perms, input_serializer, ai metadata và list_query_serializer.
    """
    required_perms: tuple = ()           # T2 — đặt được qua @action(required_perms=...)
    input_serializer = None              # serializer đầu vào của @action
    ai: AiMeta | None = None             # AiMeta cho action — đặt qua @action(ai=AiMeta(...))
    ai_by_action: dict = {}              # AiMeta cho list/retrieve/create/partial_update
    list_query_serializer = None         # tham số lọc của list (get_queryset cũng dùng nó)
