"""
Định dạng CHUỖI cho người đọc (thông điệp lỗi, nhãn timeline, `__str__`, output lệnh quản trị).

Quy ước hiển thị (Duy 30/09, P8 Lô 8 SR-25):
- Tiền: VNĐ, dấu chấm ngăn nghìn, một dấu cách thường trước `₫` — `300000` → `300.000 ₫`.
- Giờ/ngày: luôn `Asia/Ho_Chi_Minh` (GMT+7) qua `timezone.localtime`, không `strftime` trên datetime UTC.
Dữ liệu lưu DB vẫn UTC; ISO trả qua API giữ nguyên (có offset) — file này CHỈ dành cho chuỗi người đọc.
"""
from decimal import ROUND_HALF_UP, Decimal

from django.utils import timezone


def format_vnd(amount) -> str:
    """540000 → "540.000 ₫". Làm tròn nguyên đồng half-up, không dùng float (bất biến #7). `None` → "—"."""
    if amount is None:
        return "\u2014"
    rounded = Decimal(amount).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return f"{int(rounded):,}".replace(",", ".") + " ₫"


def format_vnd_ui(amount) -> str:
    """540000 → "540.000 đ" (UI-RULES §1.6 của ERP). Dành riêng cho nhãn dòng thời gian; `format_vnd` (₫) giữ nguyên cho Shop (SR-25)."""
    return format_vnd(amount).replace(" ₫", " đ")


def format_local_time(value) -> str:
    """Giờ VN dạng `HH:MM`. `value` phải là datetime có múi giờ."""
    return timezone.localtime(value).strftime("%H:%M")


def format_local_date(value) -> str:
    """Ngày VN dạng `YYYY-MM-DD`. `value` phải là datetime có múi giờ."""
    return timezone.localtime(value).strftime("%Y-%m-%d")


def format_local_datetime(value) -> str:
    """Ngày giờ VN dạng `YYYY-MM-DD HH:MM`. `value` phải là datetime có múi giờ."""
    return timezone.localtime(value).strftime("%Y-%m-%d %H:%M")
