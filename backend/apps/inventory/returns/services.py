"""Duyệt hàng giao thất bại về kho (P-08, BR-HV): tái nhập đúng lô gốc hoặc huỷ bỏ (lỗ)."""
from decimal import Decimal

from django.db import transaction

from apps.common.audit import record_audit
from apps.common.exceptions import BusinessError
from apps.inventory.models import ReturnToStock, StockLedgerEntry
from apps.inventory.stock import services as stock

ZERO = Decimal("0")


def apply_return(*, return_to_stock, approver):
    """
    Duyệt hàng hoàn (BR-HV). RESTOCK: cộng lại đúng lô gốc (BR-HV-01). WRITE_OFF:
    không cộng lại, ghi nhận lỗ. Lô đã chốt không nhận hàng hoàn (BR-HV-04).
    """
    rt = return_to_stock
    if rt.status != ReturnToStock.Status.APPROVED and rt.status != ReturnToStock.Status.DRAFT:
        raise BusinessError("Trạng thái phiếu hàng hoàn không hợp lệ.")
    if rt.status == ReturnToStock.Status.APPROVED:
        raise BusinessError("Phiếu hàng hoàn đã được duyệt.")
    if rt.decision == ReturnToStock.Decision.PENDING:
        raise BusinessError("Phải chọn Tái nhập hoặc Huỷ bỏ trước khi duyệt (BR-HV-02).")
    if rt.batch.is_closed:
        raise BusinessError("Lô đã chốt không nhận hàng hoàn (BR-HV-04).")

    with transaction.atomic():
        if rt.decision == ReturnToStock.Decision.RESTOCK:
            stock.record_movement(
                batch=rt.batch, qty_change=rt.qty,
                movement_type=StockLedgerEntry.MovementType.RETURN_RESTOCK,
                reference=f"return {rt.pk} (hàng hoàn)", actor=approver,
            )
        else:  # WRITE_OFF — không cộng lại, ghi nhận lỗ hàng hỏng vào lô gốc
            stock.record_movement(
                batch=rt.batch, qty_change=ZERO,
                movement_type=StockLedgerEntry.MovementType.WRITE_OFF,
                reference=f"return {rt.pk} (huỷ bỏ, lỗ {rt.qty}kg)", actor=approver,
            )
        rt.status = ReturnToStock.Status.APPROVED
        rt.approved_by = approver
        rt.save(update_fields=["status", "approved_by"])
    record_audit(
        "approve_returntostock", actor=approver, obj=rt,
        changes={"decision": {"to": rt.decision}},
    )
    return rt
