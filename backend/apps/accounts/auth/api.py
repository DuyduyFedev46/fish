"""
Endpoint module auth:
- `POST /api/auth/token/`           — đăng nhập → 200 {"token": ...}; ghi `last_login`.
- `GET  /api/auth/me/`              (S6, S47) — tôi là ai, nhóm, quyền, nhãn tiếng Việt.
- `POST /api/auth/logout/`          (S46) — thu token (C8: mọi máy văng) → 204.
- `POST /api/auth/change-password/` (S46) — tự đổi mật khẩu → 200 {"token": mới}.
"""
from django.contrib.auth import logout as django_logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import update_last_login
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.exceptions import BusinessError

from . import services

CHANGE_PASSWORD_FIELDS = ("old_password", "new_password")


class LoginTokenView(ObtainAuthToken):
    """Như `obtain_auth_token` của DRF (cùng serializer, JSON, mã lỗi; người đã nghỉ vẫn bị
    từ chối), thêm ghi `User.last_login` để cột "Đăng nhập gần nhất" ở /api/staff/ có dữ liệu."""

    allow_must_change_password = True  # BR-PQ-19: đăng nhập bằng mật khẩu tạm vẫn được

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        update_last_login(None, user)
        return Response({"token": token.key})


class MeView(APIView):
    """Tôi là ai, thuộc Group nào, có quyền gì. Người đã nghỉ / token bị thu → 401."""

    permission_classes = [IsAuthenticated]
    allow_must_change_password = True  # BR-PQ-19: miễn chặn

    def get(self, request):
        return Response(services.describe_user(request.user))


def _has_session(request):
    return getattr(request._request, "session", None) is not None


class LogoutView(APIView):
    """Đăng xuất: xoá token của người đang dùng (và phiên session nếu có)."""

    permission_classes = [IsAuthenticated]
    allow_must_change_password = True  # BR-PQ-19: miễn chặn

    def post(self, request):
        services.logout(user=request.user)
        if _has_session(request):
            django_logout(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChangePasswordView(APIView):
    """Tự đổi mật khẩu của chính mình. Chỉ nhận `old_password`, `new_password` (BR-PQ-17)."""

    permission_classes = [IsAuthenticated]
    allow_must_change_password = True  # BR-PQ-19: miễn chặn

    def post(self, request):
        data = request.data if hasattr(request.data, "keys") else {}
        unknown = sorted(set(data.keys()) - set(CHANGE_PASSWORD_FIELDS))
        if unknown:
            raise BusinessError(
                f"Trường không được phép: {', '.join(unknown)}. "
                "Chỉ đổi được mật khẩu của chính bạn.",
                code="BR-PQ-17",
            )
        token = services.change_own_password(
            user=request.user,
            old_password=data.get("old_password"),
            new_password=data.get("new_password"),
        )
        if _has_session(request) and request.auth is None:
            # Đăng nhập kiểu session: giữ phiên hiện tại sống sau khi đổi hash mật khẩu.
            request.user.refresh_from_db(fields=["password"])
            update_session_auth_hash(request._request, request.user)
        return Response({"token": token})
