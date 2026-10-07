"""
BR-PQ-19 (S48) — chặn API nghiệp vụ khi tài khoản còn phải đổi mật khẩu.

Đặt ở lớp xác thực DRF (thay `DEFAULT_AUTHENTICATION_CLASSES`) thay vì permission class, vì
nhiều view tự khai `permission_classes` riêng → permission mặc định không phủ hết; còn lớp xác
thực thì mọi view DRF đều đi qua. View được miễn khai `allow_must_change_password = True`
(me, change-password, logout, đăng nhập).

D-3 (Duy 08/10, câu 6): cùng chỗ này chặn người không thuộc nhóm nào và không phải superuser bằng
403 `AUTH_NO_ROLE`. View được miễn khai `allow_without_group = True` (đăng nhập, me, logout, đổi mật khẩu),
hoặc mọi `permission_classes` là `AllowAny` (Shop, public, internal).

Ghi chú test: `APIClient.force_authenticate` bỏ qua lớp xác thực → test S48 dùng token thật.
"""
from rest_framework import authentication
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny

MUST_CHANGE_PASSWORD_CODE = "AUTH_MUST_CHANGE_PASSWORD"
MUST_CHANGE_PASSWORD_DETAIL = (
    "Bạn cần đặt mật khẩu mới trước khi dùng hệ thống (BR-PQ-19)."
)


class MustChangePassword(PermissionDenied):
    """403 `{"detail", "code": "AUTH_MUST_CHANGE_PASSWORD"}` (render ở apps.common.api)."""

    default_detail = MUST_CHANGE_PASSWORD_DETAIL
    default_code = MUST_CHANGE_PASSWORD_CODE
    render_code = True


def must_change_password(user) -> bool:
    """Cờ hiệu lực: superuser không bị ép; người không có StaffProfile → False."""
    if user is None or not user.is_authenticated or user.is_superuser:
        return False
    profile = getattr(user, "staff_profile", None)  # RelatedObjectDoesNotExist là AttributeError
    return bool(profile and profile.must_change_password)


NO_ROLE_CODE = "AUTH_NO_ROLE"
NO_ROLE_DETAIL = (
    "Tài khoản của bạn chưa thuộc nhóm nào nên không có quyền vào hệ thống vận hành. "
    "Nhờ Chủ vựa xếp nhóm."
)


class NoRole(PermissionDenied):
    """403 `{"detail", "code": "AUTH_NO_ROLE"}` (render ở apps.common.api)."""

    default_detail = NO_ROLE_DETAIL
    default_code = NO_ROLE_CODE
    render_code = True


def has_erp_access(user) -> bool:
    """D-3: superuser, hoặc thuộc ít nhất một Group. Quyền gán trực tiếp không tính. Hỏi DB mỗi lần
    (không cache) để việc gỡ nhóm có hiệu lực ngay."""
    if user is None or not user.is_authenticated:
        return False
    return bool(user.is_superuser) or user.groups.exists()


def _is_public_view(view) -> bool:
    perms = getattr(view, "permission_classes", None) or []
    return bool(perms) and all(p is AllowAny for p in perms)


class _EnforceAccessMixin:
    def authenticate(self, request):
        result = super().authenticate(request)
        if result is not None:
            user = result[0]
            view = (getattr(request, "parser_context", None) or {}).get("view")
            if not getattr(view, "allow_must_change_password", False) and must_change_password(user):
                raise MustChangePassword()
            exempt = getattr(view, "allow_without_group", False) or _is_public_view(view)
            if not exempt and not has_erp_access(user):
                raise NoRole()
        return result


class TokenAuthentication(_EnforceAccessMixin, authentication.TokenAuthentication):
    pass


class SessionAuthentication(_EnforceAccessMixin, authentication.SessionAuthentication):
    pass
