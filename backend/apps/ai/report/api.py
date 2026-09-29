"""
API endpoint cho Báo cáo AI cuối ngày (02b §6.6, DW-22).
GET /api/ai/report/daily/?date=YYYY-MM-DD
"""
import datetime
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.report import services


class AiDailyReportView(APIView):
    """
    GET /api/ai/report/daily/?date=YYYY-MM-DD
    Chỉ dành cho Chủ vựa (quyền ai.manage_ai_policy, DW-22-AC3).
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not request.user.has_perm("ai.manage_ai_policy"):
            return Response(
                {
                    "detail": "Bạn không có quyền xem báo cáo AI của Chủ.",
                    "code": "BR-PQ-12",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        date_str = request.query_params.get("date")
        if date_str:
            try:
                report_date = datetime.date.fromisoformat(date_str)
            except ValueError:
                return Response(
                    {
                        "detail": "Định dạng ngày không hợp lệ. Sử dụng YYYY-MM-DD.",
                        "code": "INVALID_DATE",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            report_date = timezone.localdate()

        data = services.get_daily_ai_report(report_date)
        return Response(data, status=status.HTTP_200_OK)
