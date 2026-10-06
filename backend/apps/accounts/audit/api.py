"""
Endpoint nhật ký hành động — GET /api/audit-logs/ (S03).

Quyền `accounts.view_auditlog` (chu + quan_ly — data migration 0007); nv_kho/nv_giao
→ 403 (S03-AC5). Append-only: không POST/PUT/PATCH/DELETE (BR-PQ-06, bất biến 3/5).
Lọc `?date_from=&date_to=` (YYYY-MM-DD, giờ Việt Nam, gồm cả hai ngày) và `?q=` (chỉ mã chứng từ, Lô 17a ED-41-AC2).
Lọc `?actor_kind=` / `?action=` / `?actor=<user id>` (R16, ERP theo design: hoạt động của một nhân viên; chỉ các dòng
do chính người đó làm, không gồm dòng AI thay mặt hay dòng Hệ thống); phân trang theo quy ước console (StandardPagination).
Lọc giá vốn khỏi `changes` khi người gọi không có quyền xem giá vốn (S01, L-3).
"""
import datetime
import re

from django.db.models import Q
from django.utils import timezone
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.views import APIView

from apps.accounts.models import AuditLog
from apps.common.api import StandardPagination
from apps.common.cost_keys import can_view_cost
from apps.common.exceptions import BusinessError
from apps.common.params import parse_positive_id

from .serializers import audit_item, exclude_ai_rows

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


def _date_filter(request, name):
    raw = (request.query_params.get(name) or "").strip()
    if not raw:
        return None
    try:
        return datetime.date.fromisoformat(raw)
    except ValueError:
        raise BusinessError(f"Tham số {name} phải có dạng YYYY-MM-DD.", code=INVALID_FILTER) from None


def _start_of_day(day):
    """00:00 giờ Việt Nam của `day` (TIME_ZONE của dự án)."""
    return timezone.make_aware(datetime.datetime.combine(day, datetime.time.min))


CODE_QUERY = re.compile(r"^[0-9A-Za-z#._-]{2,40}$")
PHONE_LIKE = re.compile(r"\d{9,}")


def _code_query(request):
    """`?q=` chỉ tìm theo mã chứng từ. Dãy từ 9 chữ số trở lên có thể là SĐT → 400 (bất biến 9, giống tra mã phiếu giao).
    Thông điệp không lặp lại `q`."""
    raw = (request.query_params.get("q") or "").strip()
    if not raw:
        return ""
    if PHONE_LIKE.search(raw):
        raise BusinessError("Chỉ tìm theo mã chứng từ.", code=INVALID_FILTER)
    if not CODE_QUERY.match(raw):
        raise BusinessError("Mã tìm kiếm chỉ gồm chữ không dấu, số và các ký tự # . _ -, dài 2 đến 40 ký tự.", code=INVALID_FILTER)
    return raw


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
        qs = exclude_ai_rows(qs)  # AI tắt -> ẩn dòng AI ở cả count và phân trang
        action = (request.query_params.get("action") or "").strip()
        actor_kind = (request.query_params.get("actor_kind") or "").strip()
        actor_id = _actor_filter(request)
        if actor_id is not None:
            qs = qs.filter(actor_id=actor_id)
        if action:
            qs = qs.filter(action=action)
        if actor_kind:
            qs = qs.filter(actor_kind=actor_kind)

        date_from = _date_filter(request, "date_from")
        date_to = _date_filter(request, "date_to")
        if date_from and date_to and date_from > date_to:
            raise BusinessError("Ngày bắt đầu không được sau ngày kết thúc.", code=INVALID_FILTER)
        if date_from:
            qs = qs.filter(created_at__gte=_start_of_day(date_from))
        if date_to:
            qs = qs.filter(created_at__lt=_start_of_day(date_to + datetime.timedelta(days=1)))
        code = _code_query(request)
        if code:
            qs = qs.filter(Q(object_repr__icontains=code) | Q(proposal_ref__icontains=code))

        can_cost = can_view_cost(request.user)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response([audit_item(row, can_view_cost=can_cost) for row in page])
