"""
Tồn khả dụng hiển thị Shop (KHÔNG chứa giá vốn).

sellable_qty: tồn khả dụng = tồn sổ − giữ chỗ (BR-BH-01); BUNDLE tính theo thành phần
khan hiếm nhất (BR-DM-06). Chỉ tính lô còn hạn (BR-LO-02) — dùng nguồn chung
`apps.inventory.batches.services.sellable_batches`.
"""
from decimal import Decimal

from apps.catalog.models import Item

ZERO = Decimal("0")


def _simple_sellable(item):
    from apps.inventory.batches.services import sellable_batches

    total = ZERO
    for b in sellable_batches(item=item):  # loại lô quá hạn (BR-LO-02)
        total += max(ZERO, b.qty_available - b.qty_reserved)
    return total


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
