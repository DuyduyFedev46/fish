"""
Sổ chuyển động kho (append-only) — nền cho sales/purchasing/delivery/reports.

Mọi biến động kho đi qua `record_movement` để `StockLedgerEntry` là sổ append-only
đầy đủ (nền báo cáo). Chạy trong transaction + `select_for_update`; không cho tồn âm.
"""
from decimal import Decimal

from django.db import transaction

from apps.common.exceptions import BusinessError
from apps.inventory.models import Batch, StockLedgerEntry

ZERO = Decimal("0")


def record_movement(*, batch, qty_change, movement_type, reference="", actor=None):
    """Append StockLedgerEntry + cập nhật qty_available (không cho âm)."""
    qty_change = Decimal(qty_change)
    with transaction.atomic():
        b = Batch.objects.select_for_update().get(pk=batch.pk)
        new_qty = b.qty_available + qty_change
        if new_qty < ZERO:
            raise BusinessError(
                f"Xuất vượt tồn lô {b.batch_id}: còn {b.qty_available}kg, cần {-qty_change}kg."
            )
        b.qty_available = new_qty
        b.save(update_fields=["qty_available"])
        entry = StockLedgerEntry.objects.create(
            batch=b,
            movement_type=movement_type,
            qty_change=qty_change,
            reference=reference,
            created_by=actor,
        )
    return entry
