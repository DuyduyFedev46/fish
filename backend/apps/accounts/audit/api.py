"""
Endpoint nhật ký hành động — GET /api/audit-logs/ (S03).

Quyền `accounts.view_auditlog` (chu + quan_ly — data migration 0007); nv_kho/nv_giao
→ 403 (S03-AC5). Append-only: không POST/PUT/PATCH/DELETE (BR-PQ-06, bất biến 3/5).
Lọc `?actor_kind=` / `?action=` / `?actor=<user id>` (R16, ERP theo design: hoạt động của một nhân viên; chỉ các dòng
do chính người đó làm, không gồm dòng AI thay mặt hay dòng Hệ thống); phân trang theo quy ước console (StandardPagination).
Lọc giá vốn khỏi `changes` khi người gọi không có quyền xem giá vốn (S01, L-3).
"""
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.views import APIView

from apps.accounts.models import AuditLog
from apps.common.api import StandardPagination
from apps.common.cost_keys import can_view_cost
from apps.common.exceptions import BusinessError
from apps.common.params import parse_positive_id

from .serializers import audit_item

VIEW_AUDITLOG_PERM = "accounts.view_auditlog"
INVALID_FILTER = "INVALID_FILTER"


def _actor_filter(request):
    """`?actor=` → id người làm (int) hoặc None khi không gửi/để trống. Sai dạng → 400 `INVALID_FILTER`
    (thông điệp không lặp lại giá trị gửi lên)."""
    raw = request.query_params.get("actor")
    if raw is None or raw == "":
        return None
    try:
        return parse_positive_id(raw)
    except ValueError:
        raise BusinessError("Tham số actor phải là mã người dùng (số nguyên dương).", code=INVALID_FILTER) from None


class CanViewAuditLog(BasePermission):
    message = "Thiếu quyền xem nhật ký hành động."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.has_perm(VIEW_AUDITLOG_PERM))


class AuditLogListView(APIView):
    permission_classes = [IsAuthenticated, CanViewAuditLog]
    http_method_names = ["get", "head", "options"]

    def get(self, request):
        qs = AuditLog.objects.select_related("actor", "ai_actor").order_by("-created_at", "-id")
        action = (request.query_params.get("action") or "").strip()
        actor_kind = (request.query_params.get("actor_kind") or "").strip()
        actor_id = _actor_filter(request)
        if actor_id is not None:
            qs = qs.filter(actor_id=actor_id)
        if action:
            qs = qs.filter(action=action)
        if actor_kind:
            qs = qs.filter(actor_kind=actor_kind)

        can_cost = can_view_cost(request.user)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response([audit_item(row, can_view_cost=can_cost) for row in page])
