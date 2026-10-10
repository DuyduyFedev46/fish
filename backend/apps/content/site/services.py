from decimal import Decimal, InvalidOperation
from typing import Any

from django.conf import settings

# Link và ảnh "đã thông báo website TMĐT" do FE gắn vào thẻ <a>/<img> -> chỉ nhận http(s) (chặn javascript:, data:).
ALLOWED_URL_PREFIXES = ("https://", "http://")


def _clean_str(val: Any) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def _clean_url(val: Any) -> str | None:
    s = _clean_str(val)
    if s is None or not s.lower().startswith(ALLOWED_URL_PREFIXES):
        return None
    return s


def _positive_int_or_none(val: Any) -> int | None:
    """Chuỗi env số nguyên dương -> int; rỗng, sai dạng, 0 hay âm -> None (Shop ẩn câu chứa số, E3)."""
    s = _clean_str(val)
    if s is None or not s.isdigit():
        return None
    number = int(s)
    return number if number > 0 else None


def _kg_text(val: Any) -> str:
    """Số kg dạng chuỗi gọn: Decimal("1.0") -> "1", Decimal("0.50") -> "0.5" (khớp kiểu giá/số của catalog)."""
    try:
        number = Decimal(str(val))
    except (InvalidOperation, ValueError):
        return str(val)
    return format(number.normalize(), "f")


def site_info() -> dict[str, Any]:
    """
    Trả thông tin người bán và cờ go-live từ cấu hình settings (GL-01, GL-04, SHOP-5-01).
    Đọc settings mỗi lần gọi để override_settings và reload env có hiệu lực ngay lập tức.
    Dựng dict tường minh, tuyệt đối không dùng __dict__ hay vòng lặp để tránh rò rỉ secret (GL-01-AC7).
    Chỉ dữ liệu người bán, không dữ liệu khách (bất biến 9, SHOP-5-01 AC4).
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
    # seller_complete giữ nghĩa cũ: đủ 7 trường bắt buộc ở trên (02b §3.6).
    seller_complete = all(v is not None for v in seller.values())

    # BR-ND-18 (sửa 10/10): trống -> null, Shop ẩn khối tương ứng. Link/ảnh thông báo website để trống tới khi có S-14.
    seller.update({
        "zalo": _clean_str(getattr(settings, "SELLER_ZALO", "")),
        "working_hours": _clean_str(getattr(settings, "SELLER_WORKING_HOURS", "")),
        "registration_issued_by": _clean_str(getattr(settings, "SELLER_REG_ISSUED_BY", "")),
        "registration_issued_on": _clean_str(getattr(settings, "SELLER_REG_ISSUED_ON", "")),
        "website_notice_url": _clean_url(getattr(settings, "SELLER_WEBSITE_NOTICE_URL", "")),
        "website_notice_image": _clean_url(getattr(settings, "SELLER_WEBSITE_NOTICE_IMAGE", "")),
    })

    policies = {
        "return_report_hours": _positive_int_or_none(getattr(settings, "SHOP_RETURN_REPORT_HOURS", "")),
        "min_qty_kg": _kg_text(getattr(settings, "SHOP_MIN_QTY_KG", Decimal("1"))),
        "qty_step_kg": _kg_text(getattr(settings, "SHOP_QTY_STEP_KG", Decimal("0.5"))),
        "hold_minutes": int(settings.SALES_ORDER_TTL_MINUTES),
    }

    return {
        "seller": seller,
        "seller_complete": seller_complete,
        "privacy_consent_required": bool(getattr(settings, "PRIVACY_CONSENT_REQUIRED", True)),
        "confirm_call_notice": bool(getattr(settings, "SHOP_CONFIRM_CALL_NOTICE", False)),
        "confirm_call_hours": str(getattr(settings, "SHOP_CONFIRM_CALL_HOURS", "7:00–20:00")),
        "policies": policies,
    }
