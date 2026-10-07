"""
Guidance "chỉ dòng thời gian" cho nhân viên (`staff`) — Lô 2, R2 (02b §3.8).

Quyền: `accounts.manage_staff` (chỉ Chủ), giống `StaffViewSet`. Mã hiển thị là tên đăng nhập. Không đưa `changes`
(có thể chứa SĐT nhân viên) hay `note` ra ngoài.
"""
from django.contrib.auth.models import User

from apps.common.guidance.api import register_guidance
from apps.common.guidance.audit_timeline import make_audit_timeline_provider

ACTION_LABELS = {
    "staff_create": "Tạo tài khoản",
    "staff_update": "Cập nhật hồ sơ nhân viên",
    "staff_groups_change": "Đổi nhóm quyền",
    "staff_deactivate": "Ngừng tài khoản",
    "staff_reactivate": "Mở lại tài khoản",
    "staff_password_reset": "Đặt lại mật khẩu",
    "password_change_self": "Tự đổi mật khẩu",
    "admin_edit": "Sửa trong trang quản trị kỹ thuật",
}

register_guidance(
    "staff",
    make_audit_timeline_provider(
        User,
        "accounts.manage_staff",
        doc_type="staff",
        code_fn=lambda u: u.get_username(),
        action_labels=ACTION_LABELS,
        # Đăng nhập/đăng xuất là nhiễu, không phải "việc đã làm" (và làm timeline phình mãi).
        exclude_actions=frozenset({"logout", "login"}),
    ),
)
