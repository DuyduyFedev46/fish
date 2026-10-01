"""API báo cáo — lãi lỗ theo lô (nguồn sự thật) & theo kỳ. Chỉ view_profitreport (1.7)."""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.declare import AiMeta
from apps.common.api import StandardPagination, require_perm
from apps.inventory.models import Batch

from . import services
from .batch_list import batches_for_report
from .period_counts import period_counts

PERM = "reports.view_profitreport"


class BatchPnlView(APIView):
    ai = AiMeta(keywords=("báo cáo lô",))
    permission_classes = [IsAuthenticated]
    required_perms = (PERM,)

    def get(self, request, batch_id):
        require_perm(request.user, PERM)
        try:
            batch = Batch.objects.get(batch_id=batch_id)
        except Batch.DoesNotExist:
            return Response({"detail": "Không tìm thấy lô."}, status=404)
        return Response(services.batch_pnl(batch=batch))


class BatchPnlListView(APIView):
    """
    R15: `GET /api/reports/batches/?month=YYYY-MM&state=closed|provisional&page=` → danh sách `batch_pnl` của lô có
    phát sinh trong kỳ (20 lô/trang), mỗi dòng thêm `item_name`, `status`, `status_label`. Số liệu do
    `services.batch_pnl` tính, không tính lại ở đây. Toàn bộ là lãi lỗ → chỉ `view_profitreport`.
    """

    ai = AiMeta(keywords=("danh sách lô lãi lỗ",))
    permission_classes = [IsAuthenticated]
    required_perms = (PERM,)

    def get(self, request):
        require_perm(request.user, PERM)
        queryset = batches_for_report(request.query_params)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        rows = [
            {
                **services.batch_pnl(batch=batch),
                "item_name": batch.item.name,
                "status": batch.status,
                "status_label": batch.get_status_display(),
            }
            for batch in page
        ]
        return paginator.get_paginated_response(rows)


class PeriodPnlView(APIView):
    ai = AiMeta(keywords=("báo cáo kỳ",))
    permission_classes = [IsAuthenticated]
    required_perms = (PERM,)

    def get(self, request):
        require_perm(request.user, PERM)
        try:
            year = int(request.query_params["year"])
            month = int(request.query_params["month"])
        except (KeyError, ValueError):
            return Response({"detail": "Cần tham số year & month."}, status=400)
        # R15: kèm số hoá đơn / số phiếu hoàn của kỳ (cùng căn cứ với số tiền, xem period_counts.py).
        return Response({**services.period_pnl(year=year, month=month), **period_counts(year=year, month=month)})

