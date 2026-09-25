"""Kiểm kê định kỳ & hao hụt (P-09, BR-KK) — duyệt phiếu thì điều chỉnh tồn theo số đếm."""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.common.audit import record_audit
from apps.common.exceptions import BusinessError
from apps.inventory.models import StockLedgerEntry, StockReconciliation
from apps.inventory.stock import services as stock

ZERO = Decimal("0")


def apply_reconciliation(*, reconciliation, approver):
    """
    Duyệt kiểm kê -> điều chỉnh tồn theo số thực đếm (BR-KK).
    BR-KK-02: người duyệt phải khác người nhập số. Chênh dương cần lý do (BR-KK-04).
    """
    if reconciliation.status != StockReconciliation.Status.DRAFT:
        raise BusinessError("Phiếu kiểm kê đã được duyệt.")
    if approver is not None and reconciliation.created_by_id == getattr(approver, "id", None):
        raise BusinessError("Người duyệt kiểm kê phải khác người nhập số (BR-KK-02).")
    with transaction.atomic():
        for line in reconciliation.lines.select_related("batch"):
            batch = line.batch
            diff = line.counted_qty - batch.qty_available
            line.system_qty = batch.qty_available
            line.difference_qty = diff
            if diff > ZERO and not line.reason:
                raise BusinessError(
                    f"Chênh lệch dương ở lô {batch.batch_id} phải ghi lý do (BR-KK-04)."
                )
            if diff != ZERO:
                stock.record_movement(
                    batch=batch, qty_change=diff,
                    movement_type=StockLedgerEntry.MovementType.RECONCILE,
                    reference=f"reconciliation {reconciliation.pk}", actor=approver,
                )
            line.save(update_fields=["system_qty", "difference_qty"])
        reconciliation.status = StockReconciliation.Status.APPROVED
        reconciliation.approved_by = approver
        reconciliation.approved_at = timezone.now()
        reconciliation.save(update_fields=["status", "approved_by", "approved_at"])
    record_audit("approve_stockreconciliation", actor=approver, obj=reconciliation)
    return reconciliation
