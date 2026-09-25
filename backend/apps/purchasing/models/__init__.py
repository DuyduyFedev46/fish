"""
Mua hàng (P-02, P-03).

Luồng: Supplier -> PurchaseReceipt (trực tiếp tại cảng, KHÔNG qua PO, sinh Batch)
       -> PurchaseInvoice (tách riêng, is_paid=True) -> PurchaseCost (landed cost).

BR-MH-01: mỗi dòng nhập của MỘT mặt hàng sinh MỘT lô riêng (không gộp lô).
BR-MH-03: trả tiền ngay tại cảng, không công nợ nhà cung cấp (PA — câu hỏi mở #2).
BR-MH-04: Purchase Invoice tách khỏi Receipt, nhưng phải có trước khi chốt lô.

Package models/ chia theo tính năng; file này re-export để `from apps.purchasing.models import X`
và Django (app_label=purchasing) vẫn thấy đủ model — không sinh migration mới.
"""
from .suppliers import Supplier  # noqa: F401
from .receipts import PurchaseReceipt, PurchaseReceiptLine  # noqa: F401
from .invoices import PurchaseInvoice  # noqa: F401
from .costs import PurchaseCost, PurchaseCostAllocation  # noqa: F401

__all__ = [
    "Supplier",
    "PurchaseReceipt",
    "PurchaseReceiptLine",
    "PurchaseInvoice",
    "PurchaseCost",
    "PurchaseCostAllocation",
]
