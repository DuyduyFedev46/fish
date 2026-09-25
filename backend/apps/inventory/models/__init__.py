"""
Kho (P-04, P-09) — Batch là trái tim vận hành.

- Tồn quản lý THEO LÔ, không gộp theo mặt hàng (BR-KK-01).
- FIFO theo ngày nhập khi bán (BR-BH-05).
- Tồn khả dụng hiển thị Shop = qty_available − qty_reserved (BR-BH-01).
- Vòng đời lô P-04; chốt lô đông cứng lãi/lỗ (BR-LO-05).
- StockLedgerEntry: sổ chuyển động append-only — nền cho báo cáo (system-written).

Field nhạy cảm (chỉ `view_costprice`): purchase_rate, landed_unit_cost.

Package models/ chia theo tính năng; file này re-export để `from apps.inventory.models import X`
và Django (app_label=inventory) vẫn thấy đủ model — không sinh migration mới.
"""
from .warehouses import Warehouse  # noqa: F401
from .batches import Batch  # noqa: F401
from .stock import StockLedgerEntry, StockEntry  # noqa: F401
from .stocktake import StockReconciliation, StockReconciliationLine  # noqa: F401
from .returns import ReturnToStock  # noqa: F401

__all__ = [
    "Warehouse",
    "Batch",
    "StockLedgerEntry",
    "StockEntry",
    "StockReconciliation",
    "StockReconciliationLine",
    "ReturnToStock",
]
