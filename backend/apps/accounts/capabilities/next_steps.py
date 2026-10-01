"""
Guidance "chỉ dòng thời gian" cho nhóm quyền (`group`) — R2 (02b §3.8), nhật ký đổi việc của nhóm.

`GET /api/guidance/group/<pk Group>/`: quyền `accounts.manage_staff` (chỉ Chủ, giống màn Phân quyền). Chỉ có nhãn
do code dựng (Bật/Tắt việc X) — không `changes` thô. Provider được nạp theo hai đường: khoá `group` trong
`_LAZY_MODULES` của guidance (nạp khi có người gọi) và `capabilities/api.py` import module này lúc khởi động URL;
đăng ký hai lần cùng một provider là vô hại.
"""
from django.contrib.auth.models import Group

from apps.common.guidance.api import register_guidance
from apps.common.guidance.audit_timeline import make_audit_timeline_provider

from .services import ACTION_CHANGE_CAPABILITIES, capability_change_label

register_guidance(
    "group",
    make_audit_timeline_provider(
        Group,
        "accounts.manage_staff",
        doc_type="group",
        code_fn=lambda group: group.name,
        action_labels={ACTION_CHANGE_CAPABILITIES: capability_change_label},
    ),
)
