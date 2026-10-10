"""
Tồn khả dụng, mức tồn và luật số lượng của Shop (KHÔNG chứa giá vốn).

sellable_qty: tồn khả dụng = tồn sổ − giữ chỗ (BR-BH-01); BUNDLE tính theo thành phần
khan hiếm nhất (BR-DM-06). Chỉ tính lô còn hạn (BR-LO-02) — dùng nguồn chung
`apps.inventory.batches.services.sellable_batches`. Số này CHỈ dùng nội bộ (ERP, tạo đơn);
API công khai chỉ được trả `stock_level` (BR-BH-01, BR-BH-23).

stock_level / qty_rule / validate_line_qty (SHOP-2-01, SHOP-2-02): ngưỡng và bước đọc từ
settings `SHOP_MIN_QTY_KG`, `SHOP_QTY_STEP_KG`, `SHOP_LOW_STOCK_KG`, `SHOP_LOW_STOCK_COMBO` (bất biến 7).
"""
from decimal import Decimal, InvalidOperation

from django.conf import settings

from apps.catalog.models import Item

ZERO = Decimal("0")


def _simple_sellable(item):
    from apps.inventory.batches.services import sellable_batches

    total = ZERO
    for b in sellable_batches(item=item):  # loại lô quá hạn (BR-LO-02)
        total += max(ZERO, b.qty_available - b.qty_reserved)
    return total


def simple_sellable_qty(item):
    """Kg bán được của một mặt hàng thường (dùng cho kiểm cộng dồn nhu cầu khi tạo đơn)."""
    return _simple_sellable(item)


def sellable_qty(item):
    """SIMPLE: kg khả dụng. BUNDLE: số combo bán được (min theo thành phần, BR-DM-06)."""
    if item.item_type != Item.ItemType.BUNDLE:
        return _simple_sellable(item)
    best = None
    for bl in item.bundle_lines.select_related("component"):
        if bl.qty_per_bundle <= ZERO:
            continue
        comp_available = _simple_sellable(bl.component)
        combos = int(comp_available // bl.qty_per_bundle)
        best = combos if best is None else min(best, combos)
    return Decimal(best or 0)


# --- Mức tồn & luật số lượng của Shop (BR-BH-22, BR-BH-23, BR-DM-01) -----------------------

STOCK_IN = "in"
STOCK_LOW = "low"
STOCK_OUT = "out"
UNIT_KG = "kg"
UNIT_COMBO = "combo"
COMBO_STEP = Decimal("1")
MAX_LINE_QTY = Decimal("1000000")  # chặn số lượng vô lý, nhỏ hơn nhiều so với cột DB (12 chữ số)


def sale_unit(item):
    """Đơn vị bán trên Shop: SIMPLE bán theo kg, BUNDLE bán theo combo (BR-DM-01)."""
    return UNIT_COMBO if item.item_type == Item.ItemType.BUNDLE else UNIT_KG


def qty_rule(item):
    """(mức tối thiểu, bước) khi đặt. Combo luôn số nguyên từ 1 (BR-BH-22); kg đọc từ settings."""
    if item.item_type == Item.ItemType.BUNDLE:
        return COMBO_STEP, COMBO_STEP
    return Decimal(settings.SHOP_MIN_QTY_KG), Decimal(settings.SHOP_QTY_STEP_KG)


def validate_line_qty(item, qty):
    """Số lượng đặt hợp lệ: hữu hạn, không dưới mức tối thiểu, là bội của bước (BR-BH-22)."""
    qty = Decimal(qty)
    if not qty.is_finite() or qty > MAX_LINE_QTY:   # chặn "1e30": phép chia dư tràn độ chính xác (review lô 1, M1)
        return False
    min_qty, step = qty_rule(item)
    if qty < min_qty:
        return False
    try:
        return step <= ZERO or qty % step == ZERO
    except InvalidOperation:
        return False


def stock_level(item):
    """
    "in" | "low" | "out" (BR-BH-23). "out" khi tồn bán được nhỏ hơn mức tối thiểu của BR-BH-22
    (combo: dưới 1 bộ). "low" khi dưới ngưỡng cấu hình riêng cho kg và cho combo.
    """
    available = sellable_qty(item)
    if item.item_type == Item.ItemType.BUNDLE:
        if available < 1:
            return STOCK_OUT
        return STOCK_LOW if available < settings.SHOP_LOW_STOCK_COMBO else STOCK_IN
    if available < Decimal(settings.SHOP_MIN_QTY_KG):
        return STOCK_OUT
    return STOCK_LOW if available < Decimal(settings.SHOP_LOW_STOCK_KG) else STOCK_IN
