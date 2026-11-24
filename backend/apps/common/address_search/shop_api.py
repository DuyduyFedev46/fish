"""
Endpoint công khai tìm địa chỉ trên Shop qua máy chủ Cá Về (SHOP-3-04, 02b §1.9b.3, bất biến 9).

- `POST /api/shop/address-search/`: nhận `{scheme, text}`, trả `{results: [{ref, title, subtitle}]}`.
- `POST /api/shop/address-place/`: nhận `{scheme, ref}`, trả `{street, display, suggestion}`.
Chỉ nhận POST thân JSON để chữ khách gõ không rơi vào log URL của hạ tầng; không ghi log thân request.
"""
import re

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.administrative_units import catalog
from apps.common.api import NoStoreMixin
from apps.common.exceptions import BusinessError
from apps.common.throttling import ShopAddressSearchThrottle, body_dict

from . import vietmap

TEXT_MIN_LENGTH = 2
TEXT_MAX_LENGTH = 120
_REF_RE = re.compile(r"\A(auto|geocode):[A-Za-z0-9_\-+/=.:]{1,500}\Z")


def _validation_error(**fields: str) -> BusinessError:
    return BusinessError(
        "Thông tin tìm địa chỉ chưa hợp lệ.",
        code="VALIDATION",
        extra={"fields": dict(fields)},
    )


class ShopAddressSearchView(NoStoreMixin, APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ShopAddressSearchThrottle]
    http_method_names = ["post", "options"]

    def post(self, request):
        data = body_dict(request)
        fields: dict[str, str] = {}

        scheme = data.get("scheme")
        if not isinstance(scheme, str) or scheme not in catalog.SCHEMES:
            fields["scheme"] = "Kiểu địa chỉ chưa hợp lệ."

        raw_text = data.get("text")
        text = " ".join(raw_text.split()) if isinstance(raw_text, str) else ""
        if len(text) < TEXT_MIN_LENGTH or len(text) > TEXT_MAX_LENGTH:
            fields["text"] = f"Nhập từ {TEXT_MIN_LENGTH} đến {TEXT_MAX_LENGTH} ký tự để tìm địa chỉ."

        if fields:
            raise _validation_error(**fields)

        results = vietmap.search_autocomplete(scheme=scheme, text=text)
        return Response({"results": results})


class ShopAddressPlaceView(NoStoreMixin, APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ShopAddressSearchThrottle]
    http_method_names = ["post", "options"]

    def post(self, request):
        data = body_dict(request)
        fields: dict[str, str] = {}

        scheme = data.get("scheme")
        if not isinstance(scheme, str) or scheme not in catalog.SCHEMES:
            fields["scheme"] = "Kiểu địa chỉ chưa hợp lệ."

        raw_ref = data.get("ref")
        if not isinstance(raw_ref, str) or not _REF_RE.fullmatch(raw_ref):
            fields["ref"] = "Mã gợi ý địa chỉ chưa hợp lệ."

        if fields:
            raise _validation_error(**fields)

        place = vietmap.fetch_place(scheme=scheme, ref=raw_ref)
        return Response(place)
