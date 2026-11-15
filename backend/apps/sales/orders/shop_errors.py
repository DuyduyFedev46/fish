"""
Lỗi có cấu trúc của API tạo đơn Shop (02b §3.0, §3.3). Phong bì chung: `{"code", "detail", ...thêm}`
do `exception_handler` dựng từ `BusinessError.extra`.

Bất biến: payload KHÔNG chứa số kg tồn, số kg thiếu, mã lô, ngày, tên/SĐT/địa chỉ khách
(BR-BH-24, bất biến 1 và 9). `lines` chỉ có mã hàng và mức ("out" | "short").
"""

from django.conf import settings

from apps.common.exceptions import BusinessError
from apps.sales.utils import kg_vn_str, money_str

INVALID_QTY = "INVALID_QTY"
OUT_OF_STOCK = "OUT_OF_STOCK"
VALIDATION = "VALIDATION"
VOUCHER_INVALID = "VOUCHER_INVALID"
ORDER_LINE_TOO_LARGE = "ORDER_LINE_TOO_LARGE"
ORDER_TOO_LARGE = "ORDER_TOO_LARGE"
TOO_MANY_OPEN_ORDERS = "TOO_MANY_OPEN_ORDERS"

LEVEL_OUT = "out"      # hết hàng, hoặc món không còn bán
LEVEL_SHORT = "short"  # còn hàng nhưng không đủ số khách đặt


class ShopValidationError(BusinessError):
    """Gốc của lỗi Shop trả 400 với `code` + `detail` + dữ liệu cấu trúc."""

    http_status = 400
    default_code = VALIDATION
    default_detail = "Thông tin đặt hàng chưa hợp lệ."

    def __init__(self, detail=None, *, code=None, extra=None):
        super().__init__(detail or self.default_detail, code=code or self.default_code, extra=extra)


class InvalidQtyError(ShopValidationError):
    """BR-BH-22: số lượng sai mức tối thiểu hoặc bước. `lines`: [{item_code, min_qty, qty_step}]."""

    default_code = INVALID_QTY
    default_detail = "Số lượng không hợp lệ."

    def __init__(self, lines):
        # FISH-66 S1: câu dựng từ tham số (không viết cứng số). Không đưa mã BR vào câu của khách.
        min_text = kg_vn_str(settings.SHOP_MIN_QTY_KG)
        step_text = kg_vn_str(settings.SHOP_QTY_STEP_KG)
        detail = f"Món theo kg đặt từ {min_text} kg, mỗi lần thêm {step_text} kg. Combo đặt số nguyên từ 1."
        super().__init__(detail, extra={"lines": list(lines)})


class OutOfStockError(ShopValidationError):
    """BR-BH-24: lỗi hết hàng theo từng dòng. `lines`: [{item_code, stock_level: "out" | "short"}]."""

    default_code = OUT_OF_STOCK
    default_detail = "Một số món vừa hết hàng."

    def __init__(self, lines):
        super().__init__(extra={"lines": list(lines)})


class VoucherInvalidError(ShopValidationError):
    """
    BR-DM-19: mã không còn dùng được lúc đặt. `reason_code`: INVALID | EXPIRED | MIN_ORDER | USED_UP | BETTER_PROMO;
    `missing_amount` (chuỗi nguyên đồng) CHỈ có khi MIN_ORDER. Không số lượt còn lại, không dữ liệu đơn khác.
    """

    default_code = VOUCHER_INVALID
    default_detail = "Mã giảm giá không còn dùng được."

    def __init__(self, reason_code, missing_amount=None):
        extra = {"reason_code": reason_code}
        if missing_amount is not None:
            extra["missing_amount"] = money_str(missing_amount)
        super().__init__(extra=extra)


class _HotlineError(ShopValidationError):
    """BR-BH-31: vượt trần đặt online -> từ chối cả đơn, mời gọi hotline. Không có số tồn, không dữ liệu khách."""

    def __init__(self, message, *, extra=None):
        super().__init__(f"{message} Vui lòng gọi hotline {settings.SHOP_HOTLINE} để được hỗ trợ.", extra=extra)


class OrderLineTooLargeError(_HotlineError):
    """`lines`: [{item_code, max_qty}] — trần là tham số cấu hình, không phải tồn kho."""

    default_code = ORDER_LINE_TOO_LARGE

    def __init__(self, lines):
        super().__init__("Số lượng một món vượt mức đặt trực tuyến.", extra={"lines": list(lines)})


class OrderTooLargeError(_HotlineError):
    default_code = ORDER_TOO_LARGE

    def __init__(self):
        super().__init__("Giá trị đơn vượt mức đặt trực tuyến.")


class TooManyOpenOrdersError(_HotlineError):
    default_code = TOO_MANY_OPEN_ORDERS

    def __init__(self):
        super().__init__("Đang có quá nhiều đơn chưa thanh toán. Hãy thanh toán hoặc chờ đơn cũ hết hạn giữ chỗ.")


def validation_error(**fields):
    """400 VALIDATION với `fields` {tên_ô: câu cho khách}."""
    return ShopValidationError(extra={"fields": dict(fields)})
