"""API báo cáo — lãi lỗ theo lô (nguồn sự thật) & theo kỳ. Chỉ view_profitreport (1.7)."""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.declare import AiMeta
from apps.common.api import require_perm
from apps.inventory.models import Batch

from . import services

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
        return Response(services.period_pnl(year=year, month=month))

