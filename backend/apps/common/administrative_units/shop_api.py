"""
GET /api/shop/administrative-units/ — danh mục tỉnh/huyện/xã công khai, chỉ đọc (STA-01, 02b §2.1).
Chỉ trả `code`, `name` từ file tĩnh; không đọc DB, không có dữ liệu khách, không log.
"""
from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.exceptions import BusinessError
from apps.common.throttling import PublicContentThrottle

from . import catalog

LEVELS = ("province", "district", "ward")


def _error(**fields):
    return BusinessError(
        "Tham số tra cứu địa giới hành chính chưa hợp lệ.", code="VALIDATION", extra={"fields": dict(fields)}
    )


class AdministrativeUnitListView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [PublicContentThrottle]
    http_method_names = ["get", "head", "options"]

    def get(self, request):
        scheme = request.query_params.get("scheme")
        level = request.query_params.get("level")
        parent = request.query_params.get("parent") or ""

        if scheme not in catalog.SCHEMES:
            raise _error(scheme="Kiểu địa chỉ chưa hợp lệ.")
        if level not in LEVELS:
            raise _error(level="Cấp đơn vị chưa hợp lệ.")
        legacy = scheme == catalog.SCHEME_LEGACY

        if level == "province":
            units, parent_code = catalog.provinces(scheme), None
        else:
            if level == "district" and not legacy:
                raise _error(level="Địa chỉ mới không có cấp quận/huyện.")
            if not parent:
                raise _error(parent="Thiếu mã đơn vị cấp trên.")
            if level == "district":
                found = catalog.get_province(scheme, parent)
            elif legacy:
                found = catalog.get_district(scheme, parent)
            else:
                found = catalog.get_province(scheme, parent)
            if found is None:
                raise _error(parent="Không tìm thấy đơn vị cấp trên.")
            parent_code = parent
            units = catalog.districts(scheme, parent) if level == "district" else catalog.wards(scheme, parent)

        response = Response({
            "scheme": scheme,
            "level": level,
            "parent_code": parent_code,
            "items": [{"code": u.code, "name": u.name} for u in units],
        })
        response["Cache-Control"] = f"public, max-age={settings.ADMINISTRATIVE_UNITS_CACHE_SECONDS}"
        return response
