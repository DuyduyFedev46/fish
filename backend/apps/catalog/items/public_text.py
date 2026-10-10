"""
Kiểm chữ công khai của mặt hàng (SHOP-2b-01, BR-DM-25, bất biến 1 và 9).

Chữ trong `short_note`, `spec`, `storage`, `origin`, `description` hiện trên Shop cho khách ẩn danh, nên không được
chứa SĐT, giá, mã lô, tên nhà cung cấp, tên tàu hay ngày nhập lô. Hàm thuần, trả câu lỗi tiếng Việt hoặc None.
"""
import re

from apps.common.pii import has_long_digit_run

PUBLIC_TEXT_LIMITS = {"short_note": 60, "spec": 500, "storage": 500, "origin": 500, "description": 2000}

PHONE_MESSAGE = "Không ghi số điện thoại trong thông tin món."
PRICE_MESSAGE = "Không ghi giá trong thông tin món. Giá lấy từ bảng giá."
BATCH_CODE_MESSAGE = "Không ghi mã lô trong thông tin món."
SOURCE_MESSAGE = "Không ghi nhà cung cấp, tên tàu hay ngày nhập lô trong thông tin món."

_PRICE = re.compile(r"\d[\d.,\s]*\s*(?:đ|₫|vnđ|vnd|nghìn|ngàn|triệu)(?!\w)|\d+\s*k(?!\w)", re.IGNORECASE)
# Mã lô hệ thống: <MÃ HÀNG>-<yymmdd>-<5 ký tự hex> (vd CA01-261010-A1B2C).
_BATCH_CODE = re.compile(r"[A-Z0-9][A-Z0-9-]*-\d{6}-[0-9A-F]{5}", re.IGNORECASE)
_SOURCE_PHRASE = re.compile(r"nh[àa]\s*cung\s*c[ấa]p|t[êe]n\s*t[àa]u|ng[àa]y\s*nh[ậa]p|nh[ậa]p\s*l[ôo]", re.IGNORECASE)
# Số hiệu tàu cá dạng XX-12345 (2 chữ hoa, 4-6 số), không phân biệt dấu cách hay gạch nối.
_VESSEL_NUMBER = re.compile(r"(?<![A-Za-z])[A-Z]{2}[\s-]?\d{4,6}(?!\d)")
_COST_PHRASE = re.compile(r"gi[áa]\s*v[ốo]n", re.IGNORECASE)


def public_text_error(text):
    """Câu lỗi đầu tiên tìm thấy trong `text`, hoặc None nếu hợp lệ. Thứ tự: SĐT, giá, mã lô, nguồn nhập."""
    text = text or ""
    if has_long_digit_run(text):
        return PHONE_MESSAGE
    if _PRICE.search(text) or _COST_PHRASE.search(text):
        return PRICE_MESSAGE
    if _BATCH_CODE.search(text):
        return BATCH_CODE_MESSAGE
    if _SOURCE_PHRASE.search(text) or _VESSEL_NUMBER.search(text):
        return SOURCE_MESSAGE
    return None
