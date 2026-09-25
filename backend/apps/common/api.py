"""
Tiện ích tầng API dùng chung (Phase 3).

Trọng tâm: CHỐNG RÒ RỈ GIÁ VỐN (spec 1.6 — rủi ro triển khai số 1). Django Admin
ẩn cột thì dễ, nhưng DRF dùng chung serializer `fields='__all__'` sẽ trả đủ giá vốn
cho bất kỳ ai gọi được endpoint. `CostFieldSerializerMixin` loại field nhạy cảm khỏi
serializer khi user KHÔNG có `inventory.view_costprice` — kiểm bằng test gọi API
bằng token nhân viên (BR-PQ-13).
"""
from rest_framework import mixins, status, viewsets
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    MethodNotAllowed,
    NotAuthenticated,
    PermissionDenied,
)
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from .exceptions import BusinessError

VIEW_COSTPRICE_PERM = "inventory.view_costprice"


class BusinessModelPermissions(DjangoModelPermissions):
    """
    CRUD chuẩn -> kiểm auth.Permission theo model (Tầng 1). Custom @action (Tầng 2:
    publish/close/approve/confirm...) tự kiểm bằng `require_perm` trong view, nên ở
    đây chỉ cần user đã đăng nhập. GET cũng yêu cầu `view_*` perm (Tầng 1, S5).

    Method không có handler trên view (vd DELETE chứng từ, BR-PQ-10) → 405 cho mọi
    người đã đăng nhập, kể cả người thiếu perm `delete_*` (S3-AC4).
    """

    perms_map = {
        **DjangoModelPermissions.perms_map,
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
    }

    def has_permission(self, request, view):
        authenticated = bool(request.user and request.user.is_authenticated)
        method = request.method.lower()
        if authenticated and method != "options" and not hasattr(view, method):
            raise MethodNotAllowed(request.method)
        if getattr(view, "action", None) in getattr(view, "custom_perm_actions", ()):
            return authenticated
        return super().has_permission(request, view)


class CostFieldSerializerMixin:
    """
    Serializer khai `sensitive_fields = (...)`. Các field này bị loại khỏi output
    nếu request.user không có quyền xem giá vốn. Không có request trong context
    (vd gọi nội bộ) -> mặc định ẨN cho an toàn.
    """

    sensitive_fields: tuple = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.sensitive_fields:
            return
        request = self.context.get("request")
        user = getattr(request, "user", None)
        can_see = bool(user and user.has_perm(VIEW_COSTPRICE_PERM))
        if not can_see:
            for field_name in self.sensitive_fields:
                self.fields.pop(field_name, None)


# Nhóm thấy mọi đơn / khách / phiếu giao. Ai chỉ thuộc nv_giao bị giới hạn theo phiếu
# giao gán cho mình (Tầng 3 dòng, spec §1.6). Kiêm nhiệm = hợp quyền (BR-PQ-09).
FULL_SCOPE_GROUPS = frozenset({"chu", "quan_ly", "nv_kho"})


def has_full_delivery_scope(user) -> bool:
    return bool(
        user.is_superuser or user.groups.filter(name__in=FULL_SCOPE_GROUPS).exists()
    )


def require_perm(user, perm: str):
    """Chặn ở tầng service-call trong view cho custom action (Tầng 2)."""
    if not (user and user.has_perm(perm)):
        raise PermissionDenied(f"Thiếu quyền: {perm}")


class BusinessValidationError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Vi phạm quy tắc nghiệp vụ."
    default_code = "business_error"


# S6: một thông điệp 401 cho mọi trường hợp (chưa đăng nhập, token hỏng/đã thu, tài khoản đã
# nghỉ) — không tiết lộ lý do; bản dịch vi của DRF thiếu nên đặt tường minh.
UNAUTHORIZED_DETAIL = "Thông tin xác thực không hợp lệ."


def exception_handler(exc, context):
    """BusinessError (service layer) -> HTTP 400 (hoặc `http_status` của lớp con) `{"detail", "code"}` (S3)."""
    if isinstance(exc, BusinessError):
        return Response({"detail": str(exc), "code": exc.code}, status=exc.http_status)
    if isinstance(exc, APIException) and getattr(exc, "render_code", False):
        # Lỗi API mang mã riêng cho console (vd 403 AUTH_MUST_CHANGE_PASSWORD, BR-PQ-19).
        return Response({"detail": str(exc.detail), "code": exc.default_code},
                        status=exc.status_code)
    if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
        exc.detail = UNAUTHORIZED_DETAIL
    return drf_exception_handler(exc, context)


# --- BR-PQ-14 / BR-PQ-16: field do nghiệp vụ / hệ thống ghi ------------------

LOCKED_FIELD_CODE = "BR-PQ-14"
ACTOR_FIELD_CODE = "BR-PQ-16"


def reject_protected_fields(data, *, locked=(), actor=()):
    """Raise BusinessError nếu client gửi field khoá (BR-PQ-14) hoặc field người ghi (BR-PQ-16)."""
    keys = set(data.keys()) if hasattr(data, "keys") else set()
    sent_locked = [f for f in locked if f in keys]
    if sent_locked:
        raise BusinessError(
            f"Trường {', '.join(sent_locked)} chỉ đổi qua thao tác nghiệp vụ, "
            "không sửa trực tiếp (BR-PQ-14).",
            code=LOCKED_FIELD_CODE,
        )
    sent_actor = [f for f in actor if f in keys]
    if sent_actor:
        raise BusinessError(
            f"Trường {', '.join(sent_actor)} do hệ thống ghi theo người đăng nhập, "
            "không gửi từ client (BR-PQ-16).",
            code=ACTOR_FIELD_CODE,
        )


class ProtectedFieldsMixin:
    """
    Chặn sửa chung vượt state machine (S3) và giả người tạo (S4) trên ViewSet.

    - `locked_fields`: trạng thái / tồn / giá vốn / người phụ trách — chỉ đổi qua
      action nghiệp vụ (BR-PQ-14). Client gửi trong POST/PUT/PATCH → 400.
    - `actor_fields`: field người ghi chứng từ (vd `created_by`). Client
      gửi → 400 BR-PQ-16; khi tạo, hệ thống tự ghi `request.user`.

    Chặn bằng 400 có liệt kê field, không lặng lẽ bỏ qua (S3). Kiểm quyền Tầng 1
    chạy trước (`initial`), nên thiếu quyền vẫn là 403 (S3-AC6).
    """

    locked_fields: tuple = ()
    actor_fields: tuple = ()

    def reject_protected_fields(self, data):
        reject_protected_fields(data, locked=self.locked_fields, actor=self.actor_fields)

    def create(self, request, *args, **kwargs):
        self.reject_protected_fields(request.data)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        self.reject_protected_fields(request.data)
        return super().update(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(**{f: self.request.user for f in self.actor_fields})


class DocumentViewSet(
    ProtectedFieldsMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """ViewSet cho chứng từ: không có DELETE (BR-PQ-10 — huỷ bằng trạng thái)."""
