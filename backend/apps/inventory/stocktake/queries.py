"""
Truy vấn đọc phiếu kiểm kê (R8): một câu truy vấn có sẵn người sửa gần nhất và "người dùng hiện tại đã đếm chưa",
nên danh sách không bị N+1 (02b §3 B1).
"""
from django.db.models import CharField, Exists, OuterRef, Prefetch, Q, Subquery
from django.db.models.functions import Cast

from apps.accounts.models import AuditLog
from apps.inventory.models import StockReconciliation, StockReconciliationLine
from apps.inventory.stock.filters import parse_choice_list_param, parse_date_param, parse_id_param

from .services import LINES_AUDIT_ACTION

LABEL = StockReconciliation._meta.label


def _audit_of_reconciliation():
    return AuditLog.objects.filter(model_name=LABEL, object_id=OuterRef("pk_text"))


def reconciliation_queryset(user):
    """
    Phiếu kèm: người tạo/duyệt (select_related), dòng + lô + kho + mặt hàng (prefetch), và các cột suy ra:
    `last_*` (người thao tác gần nhất theo AuditLog), `edited_lines_by_me` (user từng sửa dòng số đếm).
    """
    latest = _audit_of_reconciliation().order_by("-created_at", "-id")
    lines = StockReconciliationLine.objects.select_related("batch__warehouse", "batch__item").order_by("id")
    qs = (
        StockReconciliation.objects
        .select_related("created_by__staff_profile", "approved_by__staff_profile")
        .prefetch_related(Prefetch("lines", queryset=lines))
        .annotate(
            pk_text=Cast("pk", CharField()),
            last_actor_kind=Subquery(latest.values("actor_kind")[:1]),
            last_actor_username=Subquery(latest.values("actor__username")[:1]),
            last_actor_display_name=Subquery(latest.values("actor__staff_profile__display_name")[:1]),
            last_ai_actor_username=Subquery(latest.values("ai_actor__username")[:1]),
            last_ai_actor_display_name=Subquery(latest.values("ai_actor__staff_profile__display_name")[:1]),
        )
    )
    user_id = getattr(user, "pk", None)
    if user_id is None:
        return qs
    return qs.annotate(
        edited_lines_by_me=Exists(
            _audit_of_reconciliation().filter(Q(actor_id=user_id) | Q(ai_actor_id=user_id), action=LINES_AUDIT_ACTION)
        )
    )


def filter_list(queryset, params):
    """Lọc danh sách: `status` (nhiều, cách phẩy), `warehouse` (kho của lô trong dòng), `date_from`/`date_to` (ngày kiểm kê)."""
    statuses = parse_choice_list_param(params, "status", StockReconciliation.Status.values)
    warehouse_id = parse_id_param(params, "warehouse")
    date_from = parse_date_param(params, "date_from")
    date_to = parse_date_param(params, "date_to")
    if statuses:
        queryset = queryset.filter(status__in=statuses)
    if warehouse_id is not None:
        queryset = queryset.filter(
            Exists(StockReconciliationLine.objects.filter(
                reconciliation=OuterRef("pk"), batch__warehouse_id=warehouse_id,
            ))
        )
    if date_from:
        queryset = queryset.filter(count_date__gte=date_from)
    if date_to:
        queryset = queryset.filter(count_date__lte=date_to)
    return queryset
