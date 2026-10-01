"""
Danh sách lãi lỗ theo lô cho màn Báo cáo (R15, 02b §3.8).

Chỉ chọn lô và gọi `services.batch_pnl` cho từng lô — KHÔNG tính lại công thức lãi lỗ ở đây.

Lô "có phát sinh trong kỳ" (tháng theo giờ VN) là một trong ba:
- nhập trong tháng (`received_date`);
- có dòng bán của hoá đơn CHƯA huỷ xuất trong tháng (`issued_at`);
- chốt trong tháng (`closed_at`).
`state=closed|provisional` lọc theo trạng thái chốt (BR-BC-05: chưa `CLOSED` là "tạm tính"); không truyền = cả hai.
"""
from django.db.models import Exists, OuterRef, Q

from apps.common.params import month_bounds
from apps.inventory.models import Batch
from apps.inventory.stock.filters import parse_choice_list_param
from apps.sales.models import SalesInvoice, SalesInvoiceLineBatch

STATE_CLOSED = "closed"
STATE_PROVISIONAL = "provisional"


def batches_for_report(params):
    queryset = Batch.objects.select_related("item")
    month = params.get("month") or ""  # không strip: "\n2026-09" phải bị từ chối
    if month:
        start, end = month_bounds(month)
        sold_in_month = SalesInvoiceLineBatch.objects.filter(
            batch=OuterRef("pk"),
            invoice_line__invoice__issued_at__gte=start,
            invoice_line__invoice__issued_at__lt=end,
        ).exclude(invoice_line__invoice__status=SalesInvoice.Status.CANCELLED)
        queryset = queryset.filter(
            Q(received_date__gte=start.date(), received_date__lt=end.date())
            | Q(closed_at__gte=start, closed_at__lt=end)
            | Exists(sold_in_month)
        )
    states = parse_choice_list_param(params, "state", (STATE_CLOSED, STATE_PROVISIONAL))
    if states and len(set(states)) == 1:
        closed = Q(status=Batch.Status.CLOSED)
        queryset = queryset.filter(closed if states[0] == STATE_CLOSED else ~closed)
    return queryset.order_by("-received_date", "-id")
