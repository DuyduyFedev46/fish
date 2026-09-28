"""
Danh sách khoá giá vốn và hàm lọc giá vốn dùng chung (S01 / L-3).

Bất biến #1: Không rò giá vốn (BR-PQ-13, BR-GV-03).
Khoá mang giá vốn / giá mua / chi phí / lãi lỗ trong mọi JSON tự do (AuditLog.changes,
và các module sau này).
Quy ước: giá BÁN khi ghi audit dùng khoá khác ("price", "sell_rate", "amount"), không dùng "rate".
"""
from apps.common.api import VIEW_COSTPRICE_PERM

# Khoá mang giá vốn / giá mua / lãi lỗ trong mọi JSON tự do (AuditLog.changes, sau này guidance).
COST_KEYS = frozenset({
    "purchase_rate", "landed_unit_cost", "unit_cost", "rate",          # Batch, PurchaseReceiptLine, *LineBatch
    "allocated_amount", "purchase_cost", "allocated_cost", "total_cost",  # PurchaseCost / batch_pnl
    "shrinkage_cost", "damage_cost", "cogs", "profit",
})


def can_view_cost(user) -> bool:
    """Kiểm tra user có quyền xem giá vốn hay không."""
    return bool(user and user.has_perm(VIEW_COSTPRICE_PERM))


def redact_cost(value):
    """
    Trả BẢN SAO đã bỏ mọi khoá thuộc COST_KEYS ở mọi độ sâu (dict lồng, list).
    Không sửa input (immutable).
    """
    if isinstance(value, dict):
        return {k: redact_cost(v) for k, v in value.items() if k not in COST_KEYS}
    if isinstance(value, list):
        return [redact_cost(v) for v in value]
    return value
