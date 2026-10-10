"""
Lỗi có cấu trúc của API tạo đơn Shop (02b §3.0, §3.3). Phong bì chung: `{"code", "detail", ...thêm}`
do `exception_handler` dựng từ `BusinessError.extra`.

Bất biến: payload KHÔNG chứa số kg tồn, số kg thiếu, mã lô, ngày, tên/SĐT/địa chỉ khách
(BR-BH-24, bất biến 1 và 9). `lines` chỉ có mã hàng và mức ("out" | "short").
"""
from apps.common.exceptions import BusinessError

INVALID_QTY = "INVALID_QTY"
OUT_OF_STOCK = "OUT_OF_STOCK"
VALIDATION = "VALIDATION"

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
        super().__init__(extra={"lines": list(lines)})


class OutOfStockError(ShopValidationError):
    """BR-BH-24: lỗi hết hàng theo từng dòng. `lines`: [{item_code, stock_level: "out" | "short"}]."""

    default_code = OUT_OF_STOCK
    default_detail = "Một số món vừa hết hàng."

    def __init__(self, lines):
        super().__init__(extra={"lines": list(lines)})


def validation_error(**fields):
    """400 VALIDATION với `fields` {tên_ô: câu cho khách}."""
    return ShopValidationError(extra={"fields": dict(fields)})
