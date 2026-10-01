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
    # P8 SR-01 (BM-01): khoá tiền suy ra được giá vốn (số kg đã biết -> chia ra đơn giá vốn).
    "loss_amount", "loss", "inventory_value", "margin", "gross_profit", "expired_cost",
    "supplier_refund_amount", "supplier_return_cost",
    # R10 (Lô 10): tiền mua của phiếu nhập (Σ số kg x đơn giá mua) và thành tiền từng dòng nhập.
    "purchase_amount",
    # B3 (Lô 11): tổng tiền mua của một nhà cung cấp (Σ số kg x đơn giá mua các phiếu đã ghi nhận).
    "purchase_total",
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
