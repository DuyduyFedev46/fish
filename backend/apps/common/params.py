"""
Đọc tham số từ request dùng chung cho nhiều app.

`parse_positive_id`: id nguyên dương cho tham số lọc (`?order=`, `?customer=`, `?assigned_to=`...) và id trong body.
Chỉ nhận chữ số ASCII, tối đa 19 ký tự và không vượt int64. Kiểm độ dài TRƯỚC khi đổi sang số, vì Python từ chối đổi
chuỗi quá 4300 chữ số bằng `ValueError` (sẽ thành 500 nếu không chặn trước), và DB báo `OverflowError` khi id lớn hơn int64.

`month_bounds`: tháng `YYYY-MM` của tham số lọc `?month=` → [đầu tháng, đầu tháng sau) theo giờ VN (ERP theo design, R3/R9).
"""
import datetime
import re

from django.utils import timezone

from apps.common.exceptions import BusinessError

MAX_ID = 2**63 - 1  # int64
MAX_ID_LENGTH = len(str(MAX_ID))  # 19


def parse_positive_id(raw) -> int:
    """Trả id (int, 1..MAX_ID). Mọi giá trị khác (rỗng, chữ, âm, 0, dấu +, khoảng trắng, chữ số Unicode, quá int64,
    không phải chuỗi) raise `ValueError`; nơi gọi tự đổi thành lỗi 400 phù hợp."""
    if not isinstance(raw, str):
        raise ValueError("id phải là chuỗi chữ số")
    if not raw.isascii() or not raw.isdigit() or len(raw) > MAX_ID_LENGTH:
        raise ValueError("id không hợp lệ")
    value = int(raw)
    if not 1 <= value <= MAX_ID:
        raise ValueError("id ngoài khoảng cho phép")
    return value


MONTH_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}")  # ASCII; fullmatch nên không nhận "\n" cuối
MONTH_MIN_YEAR, MONTH_MAX_YEAR = 2000, 2100
INVALID_FILTER = "INVALID_FILTER"


def month_bounds(raw):
    """`YYYY-MM` → (đầu tháng, đầu tháng sau) là datetime có múi giờ theo giờ hiện tại của Django (GMT+7).
    Sai dạng, tháng ngoài 01..12 hoặc năm ngoài 2000..2100 → `BusinessError` 400 mã `INVALID_FILTER`;
    thông điệp chỉ nêu tên tham số, không lặp lại giá trị gửi lên."""
    try:
        if not isinstance(raw, str) or not MONTH_PATTERN.fullmatch(raw):
            raise ValueError("month không đúng dạng")
        year, month = int(raw[:4]), int(raw[5:])
        if not MONTH_MIN_YEAR <= year <= MONTH_MAX_YEAR:
            raise ValueError("năm ngoài khoảng")
        first = datetime.date(year, month, 1)
        following = datetime.date(year + (month == 12), month % 12 + 1, 1)
    except (ValueError, OverflowError):
        raise BusinessError("Tham số month phải có dạng YYYY-MM.", code=INVALID_FILTER) from None
    tz = timezone.get_current_timezone()
    return (
        timezone.make_aware(datetime.datetime.combine(first, datetime.time.min), tz),
        timezone.make_aware(datetime.datetime.combine(following, datetime.time.min), tz),
    )
