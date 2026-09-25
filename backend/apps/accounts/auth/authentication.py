"""
BR-PQ-19 (S48) — chặn API nghiệp vụ khi tài khoản còn phải đổi mật khẩu.

Đặt ở lớp xác thực DRF (thay `DEFAULT_AUTHENTICATION_CLASSES`) thay vì permission class, vì
nhiều view tự khai `permission_classes` riêng → permission mặc định không phủ hết; còn lớp xác
thực thì mọi view DRF đều đi qua. View được miễn khai `allow_must_change_password = True`
(me, change-password, logout, đăng nhập).

Ghi chú test: `APIClient.force_authenticate` bỏ qua lớp xác thực → test S48 dùng token thật.
"""
from rest_framework import authentication
from rest_framework.exceptions import PermissionDenied

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


class _EnforcePasswordChangeMixin:
    def authenticate(self, request):
        result = super().authenticate(request)
        if result is not None:
            view = (getattr(request, "parser_context", None) or {}).get("view")
            exempt = getattr(view, "allow_must_change_password", False)
            if not exempt and must_change_password(result[0]):
                raise MustChangePassword()
        return result


class TokenAuthentication(_EnforcePasswordChangeMixin, authentication.TokenAuthentication):
    pass


class SessionAuthentication(_EnforcePasswordChangeMixin, authentication.SessionAuthentication):
    pass
