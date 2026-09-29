from typing import Any
from django.conf import settings


def _clean_str(val: Any) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def site_info() -> dict[str, Any]:
    """
    Trả thông tin người bán và cờ go-live từ cấu hình settings (GL-01, GL-04).
    Đọc settings mỗi lần gọi để override_settings và reload env có hiệu lực ngay lập tức.
    Dựng dict tường minh, tuyệt đối không dùng __dict__ hay vòng lặp để tránh rò rỉ secret (GL-01-AC7).
    """
    seller = {
        "name": _clean_str(getattr(settings, "SELLER_NAME", "")),
        "business_type": _clean_str(getattr(settings, "SELLER_BUSINESS_TYPE", "")),
        "registration_no": _clean_str(getattr(settings, "SELLER_REG_NO", "")),
        "tax_code": _clean_str(getattr(settings, "SELLER_TAX_CODE", "")),
        "address": _clean_str(getattr(settings, "SELLER_ADDRESS", "")),
        "phone": _clean_str(getattr(settings, "SELLER_PHONE", "")),
        "email": _clean_str(getattr(settings, "SELLER_EMAIL", "")),
    }
    seller_complete = all(v is not None for v in seller.values())

    return {
        "seller": seller,
        "seller_complete": seller_complete,
        "privacy_consent_required": bool(getattr(settings, "PRIVACY_CONSENT_REQUIRED", True)),
        "confirm_call_notice": bool(getattr(settings, "SHOP_CONFIRM_CALL_NOTICE", False)),
        "confirm_call_hours": str(getattr(settings, "SHOP_CONFIRM_CALL_HOURS", "7:00–20:00")),
    }
