"""
Đổi mọi `Decimal` trong kết quả báo cáo thành CHUỖI ở tầng API (TL12-num, Lô 17a).

Lý do: DRF mặc định đổi Decimal thành float khi trả JSON, làm mất độ chính xác của tiền (Decimal, bất biến 7).
Tiền → 2 chữ số thập phân ("1000000.00"); kg (khoá `qty_*` hoặc `*_qty`) → 3 chữ số ("50.000"), đúng độ chính xác của
cột kho. `int`, `bool`, chuỗi giữ nguyên. Hàm không thêm hay bớt khoá nên quy tắc giá vốn không đổi.
`services.batch_pnl`/`period_pnl` vẫn trả Decimal (AI và test service dùng trực tiếp).
"""
from decimal import ROUND_HALF_UP, Decimal

MONEY_PLACES = Decimal("0.01")
KG_PLACES = Decimal("0.001")


def _is_kg_key(key) -> bool:
    return isinstance(key, str) and (key.startswith("qty_") or key.endswith("_qty"))


def _format(value: Decimal, key) -> str:
    places = KG_PLACES if _is_kg_key(key) else MONEY_PLACES
    return str(value.quantize(places, rounding=ROUND_HALF_UP))


def stringify_decimals(value, key=None):
    if isinstance(value, Decimal):
        return _format(value, key)
    if isinstance(value, dict):
        return {k: stringify_decimals(v, k) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [stringify_decimals(v, key) for v in value]
    return value
