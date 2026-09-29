from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.throttling import PublicContentThrottle
from apps.content.site.services import site_info


class SiteInfoView(APIView):
    """
    API công khai cung cấp thông tin người bán và cờ go-live cho Shop web (GL-01, GL-04, CS-10).
    AllowAny, chỉ GET/HEAD/OPTIONS (POST/PUT/PATCH/DELETE -> 405).
    Header Cache-Control: public, max-age=300.
    """
    permission_classes = [AllowAny]
    throttle_classes = [PublicContentThrottle]
    http_method_names = ["get", "head", "options"]

    def get(self, request, *args, **kwargs):
        data = site_info()
        data["cskh_notice"] = {
            "enabled": bool(getattr(settings, "CSKH_NOTICE_ENABLED", True)),
            "working_hours": str(getattr(settings, "CSKH_WORKING_HOURS", "07:00-21:00")),
            "max_attempts": int(getattr(settings, "CSKH_MAX_UNREACHABLE_ATTEMPTS", 3)),
            "window_minutes": int(getattr(settings, "CSKH_UNREACHABLE_WINDOW_MINUTES", 30)),
            "decision_minutes": int(getattr(settings, "CSKH_MANAGER_DECISION_MINUTES", 30)),
            "auto_cancel_enabled": bool(getattr(settings, "CSKH_AUTO_CANCEL_ENABLED", False)),
            "refund_deadline_days": int(getattr(settings, "REFUND_DEADLINE_DAYS", 30)),
            "hotline": str(getattr(settings, "SHOP_HOTLINE", "")),
        }
        resp = Response(data)
        resp["Cache-Control"] = "public, max-age=300"
        return resp
