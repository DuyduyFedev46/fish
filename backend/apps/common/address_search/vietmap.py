"""
Gọi API VietMap Autocomplete v4 và Place v4 từ máy chủ Cá Về (SHOP-3-04, 02b §1.9b.3, bất biến 9).

Nguyên tắc an toàn:
- Host và đường dẫn là hằng số; tham số chỉ đi qua `urllib.parse.urlencode` (chặn SSRF).
- Key đọc động từ `settings.VIETMAP_API_KEY`; thiếu key trả ngay 503 mà không mở kết nối.
- Bỏ hoàn toàn toạ độ (`lat`, `lng`), `ward_id`, `city_id`, `boundaries` trước khi trả về.
- Tuyệt đối không ghi `text`, `ref`, URL hay `apikey` vào log; khi lỗi chỉ ghi mã trạng thái và tên API.
"""
import json
import logging
import urllib.request
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

from django.conf import settings

from apps.common.administrative_units.addresses import STREET_MAX
from apps.common.exceptions import BusinessError

from .matching import match_administrative_unit

logger = logging.getLogger(__name__)

VIETMAP_HOST = "https://maps.vietmap.vn"
AUTOCOMPLETE_PATH = "/api/autocomplete/v4"
PLACE_PATH = "/api/place/v4"
# Hằng tâm Phan Thiết để xếp hạng kết quả gần (02b §1.9b.3), KHÔNG phải vị trí của khách.
FOCUS_CENTER = "10.9289,108.1021"
MAX_RESULTS = 6
DISPLAY_TYPES = {
    "current": "1",
    "legacy": "2",
}


class AddressSearchUnavailableError(BusinessError):
    """503 khi máy chủ chưa cấu hình key hoặc VietMap lỗi / quá giờ / trả dữ liệu hỏng."""

    http_status = 503

    def __init__(self):
        super().__init__(
            "Chưa tìm được địa chỉ lúc này. Bạn gõ địa chỉ trực tiếp nhé.",
            code="ADDRESS_SEARCH_UNAVAILABLE",
        )


def _collapse_whitespace(value: Any) -> str:
    return " ".join(value.split()) if isinstance(value, str) else ""


def _require_api_key() -> str:
    api_key = str(getattr(settings, "VIETMAP_API_KEY", "") or "").strip()
    if not api_key:
        raise AddressSearchUnavailableError()
    return api_key


def _request_json(path: str, params: dict[str, str], *, api_name: str) -> Any:
    url = f"{VIETMAP_HOST}{path}?{urlencode(params)}"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    timeout = getattr(settings, "VIETMAP_TIMEOUT_SECONDS", 4)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw_bytes = response.read()
        return json.loads(raw_bytes.decode("utf-8"))
    except HTTPError as exc:
        logger.warning("vietmap upstream failed status=%s api=%s", int(exc.code), api_name)
        raise AddressSearchUnavailableError() from None
    except TimeoutError:
        logger.warning("vietmap upstream failed status=%s api=%s", "timeout", api_name)
        raise AddressSearchUnavailableError() from None
    except URLError as exc:
        status_label = "timeout" if isinstance(getattr(exc, "reason", None), TimeoutError) else "network_error"
        logger.warning("vietmap upstream failed status=%s api=%s", status_label, api_name)
        raise AddressSearchUnavailableError() from None
    except ValueError:
        logger.warning("vietmap upstream failed status=%s api=%s", "invalid_json", api_name)
        raise AddressSearchUnavailableError() from None
    except OSError:
        logger.warning("vietmap upstream failed status=%s api=%s", "network_error", api_name)
        raise AddressSearchUnavailableError() from None


def search_autocomplete(*, scheme: str, text: str) -> list[dict[str, str]]:
    """Gọi Autocomplete v4 và rút gọn tối đa 6 gợi ý `{ref, title, subtitle}`."""
    api_key = _require_api_key()
    payload = _request_json(
        AUTOCOMPLETE_PATH,
        {
            "apikey": api_key,
            "text": text,
            "display_type": DISPLAY_TYPES[scheme],
            "focus": FOCUS_CENTER,
        },
        api_name="autocomplete",
    )
    if not isinstance(payload, list):
        logger.warning("vietmap upstream failed status=%s api=%s", "invalid_json", "autocomplete")
        raise AddressSearchUnavailableError()

    results: list[dict[str, str]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        raw_ref = item.get("ref_id")
        if not isinstance(raw_ref, str) or not raw_ref:
            continue
        results.append({
            "ref": raw_ref,
            "title": _collapse_whitespace(item.get("name")),
            "subtitle": _collapse_whitespace(item.get("address")),
        })
        if len(results) >= MAX_RESULTS:
            break
    return results


def _compose_street(payload: dict[str, Any]) -> str:
    raw_address = _collapse_whitespace(payload.get("address"))
    raw_hs_num = _collapse_whitespace(payload.get("hs_num"))
    raw_street = _collapse_whitespace(payload.get("street"))
    raw_name = _collapse_whitespace(payload.get("name"))

    base_address = raw_address or " ".join(part for part in (raw_hs_num, raw_street) if part)
    if not base_address:
        combined = raw_name
    elif raw_name and raw_name.casefold() != base_address.casefold():
        combined = f"{raw_name}, {base_address}"
    else:
        combined = base_address

    return " ".join(combined.split())[:STREET_MAX].rstrip()


def fetch_place(*, scheme: str, ref: str) -> dict[str, Any]:
    """Gọi Place v4, bỏ toạ độ và mã riêng VietMap, trả `{street, display, suggestion}`."""
    api_key = _require_api_key()
    payload = _request_json(
        PLACE_PATH,
        {
            "apikey": api_key,
            "refid": ref,
        },
        api_name="place",
    )
    if not isinstance(payload, dict):
        logger.warning("vietmap upstream failed status=%s api=%s", "invalid_json", "place")
        raise AddressSearchUnavailableError()

    street = _compose_street(payload)
    display = _collapse_whitespace(payload.get("display")) or street
    suggestion = match_administrative_unit(
        scheme=scheme,
        city=_collapse_whitespace(payload.get("city")),
        district=_collapse_whitespace(payload.get("district")),
        ward=_collapse_whitespace(payload.get("ward")),
    )
    return {
        "street": street,
        "display": display,
        "suggestion": suggestion,
    }
