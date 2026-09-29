"""
API công khai cung cấp thông tin chung cho Shop web (CS-10, 02b §4.4).
- AllowAny, chỉ GET
- Cache-Control: public, max-age=300
- Không rò giá vốn hay bất kỳ dữ liệu nội bộ
"""
from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class PublicSiteInfoView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        cskh_notice = {
            "enabled": bool(getattr(settings, "CSKH_NOTICE_ENABLED", True)),
            "working_hours": str(getattr(settings, "CSKH_WORKING_HOURS", "07:00-21:00")),
            "max_attempts": int(getattr(settings, "CSKH_MAX_UNREACHABLE_ATTEMPTS", 3)),
            "window_minutes": int(getattr(settings, "CSKH_UNREACHABLE_WINDOW_MINUTES", 30)),
            "decision_minutes": int(getattr(settings, "CSKH_MANAGER_DECISION_MINUTES", 30)),
            "auto_cancel_enabled": bool(getattr(settings, "CSKH_AUTO_CANCEL_ENABLED", False)),
            "refund_deadline_days": int(getattr(settings, "REFUND_DEADLINE_DAYS", 30)),
            "hotline": str(getattr(settings, "SHOP_HOTLINE", "")),
        }
        resp = Response({"cskh_notice": cskh_notice})
        resp["Cache-Control"] = "public, max-age=300"
        return resp
