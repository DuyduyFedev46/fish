"""
Báo cáo giá vốn & lãi lỗ (P-10, mục 12 business-process-spec.md).

Hai góc nhìn (12.1):
- `batch_pnl`  : lãi/lỗ THEO LÔ — nguồn sự thật, tính lại từ `landed_unit_cost`
  hiện hành (BR-BC-04), không dùng số ảnh chụp trên đơn. Lô chưa `CLOSED` phải
  gắn nhãn "tạm tính" (BR-BC-05).
- `period_pnl` : lãi/lỗ THEO KỲ (tháng) — điều hành, doanh thu/giá vốn ghi nhận
  cùng thời điểm xác nhận thanh toán (BR-BC-01/02), hoàn tiền tính vào kỳ phát
  sinh hoàn, không sửa ngược kỳ cũ (BR-BC-03).

Không có bảng dữ liệu riêng — mọi thứ tính lại từ sales/inventory/purchasing.
"""
from decimal import Decimal

from apps.common.exceptions import BusinessError
from apps.inventory.models import Batch, ReturnToStock, StockLedgerEntry
from apps.sales.models import Refund, SalesInvoice

ZERO = Decimal("0")


def batch_pnl(*, batch):
    """
    Lãi/lỗ theo lô (nguồn sự thật, BR-BC-04):
        Lãi/lỗ = doanh thu bán từ lô − (giá mua + chi phí phân bổ + hao hụt + hàng hỏng)

    - doanh thu bán từ lô = Σ(SalesInvoiceLineBatch.qty × rate dòng hoá đơn tương ứng).
    - giá mua = purchase_rate × qty_received (chưa gồm chi phí phụ).
    - chi phí phân bổ = Σ PurchaseCostAllocation.allocated_amount của lô.
    - hao hụt = kg âm từ kiểm kê (StockLedgerEntry.RECONCILE < 0) định giá theo
      landed_unit_cost HIỆN HÀNH.
    - hàng hỏng = kg đã duyệt Huỷ bỏ (ReturnToStock.WRITE_OFF, APPROVED) định giá
      theo landed_unit_cost hiện hành.
    - Lô chưa CLOSED -> "provisional": True (BR-BC-05, nhãn "tạm tính").
    """
    if batch is None:
        raise BusinessError("Thiếu lô để tính báo cáo lãi lỗ.")

    revenue = ZERO
    qty_sold = ZERO
    for alloc in batch.sold_allocations.select_related("invoice_line").all():
        revenue += alloc.qty * alloc.invoice_line.rate
        qty_sold += alloc.qty

    purchase_cost = batch.purchase_rate * batch.qty_received
    allocated_cost = sum(
        (a.allocated_amount for a in batch.cost_allocations.all()), ZERO
    )

    shrinkage_qty = ZERO
    for entry in batch.ledger_entries.filter(
        movement_type=StockLedgerEntry.MovementType.RECONCILE, qty_change__lt=ZERO
    ):
        shrinkage_qty += -entry.qty_change
    shrinkage_cost = shrinkage_qty * batch.landed_unit_cost

    damage_qty = ZERO
    for rt in batch.returns.filter(
        decision=ReturnToStock.Decision.WRITE_OFF, status=ReturnToStock.Status.APPROVED
    ):
        damage_qty += rt.qty
    damage_cost = damage_qty * batch.landed_unit_cost

    total_cost = purchase_cost + allocated_cost + shrinkage_cost + damage_cost
    profit = revenue - total_cost

    return {
        "batch_id": batch.batch_id,
        "provisional": batch.status != Batch.Status.CLOSED,  # BR-BC-05
        "qty_received": batch.qty_received,
        "qty_sold": qty_sold,
        "landed_unit_cost": batch.landed_unit_cost,
        "revenue": revenue,
        "purchase_cost": purchase_cost,
        "allocated_cost": allocated_cost,
        "shrinkage_qty": shrinkage_qty,
        "shrinkage_cost": shrinkage_cost,
        "damage_qty": damage_qty,
        "damage_cost": damage_cost,
        "total_cost": total_cost,
        "profit": profit,
    }


def period_pnl(*, year, month):
    """
    Lãi/lỗ theo kỳ (tháng, điều hành):
        Lãi/lỗ = doanh thu ghi nhận trong kỳ − giá vốn ghi nhận cùng kỳ − hoàn tiền
        phát sinh trong kỳ.

    - doanh thu: SalesInvoice.amount có issued_at thuộc tháng (BR-BC-01), chỉ hoá
      đơn còn hiệu lực (status=ISSUED).
    - giá vốn: Σ SalesInvoiceLineBatch.qty × unit_cost (ảnh chụp lúc bán) của các
      hoá đơn trong kỳ (BR-BC-02) — KHÔNG tính lại theo landed_unit_cost hiện hành,
      khác với `batch_pnl`.
    - hoàn tiền: Σ Refund.amount có status=REFUNDED và confirmed_at thuộc tháng
      (BR-BC-03/BR-HT-06) — ghi vào kỳ phát sinh hoàn, không sửa ngược kỳ cũ. Chỉ phiếu
      gắn hoá đơn (S13-AC5).
    """
    if not year or not month:
        raise BusinessError("Thiếu năm/tháng để tính báo cáo theo kỳ.")

    invoices = SalesInvoice.objects.filter(
        status=SalesInvoice.Status.ISSUED, issued_at__year=year, issued_at__month=month,
    )
    revenue = sum((inv.amount for inv in invoices), ZERO)

    cogs = ZERO
    for inv in invoices.prefetch_related("lines__batch_allocations"):
        for line in inv.lines.all():
            for alloc in line.batch_allocations.all():
                cogs += alloc.qty * alloc.unit_cost

    # S13-AC5: phiếu hoàn gắn giao dịch KHÔNG có hoá đơn (tiền về sau huỷ / thiếu / thừa) chưa
    # từng ghi doanh thu (BR-TT-06) → không trừ vào lãi kỳ; chỉ trả lại tiền khách.
    refunds_qs = Refund.objects.filter(
        status=Refund.Status.REFUNDED, confirmed_at__year=year, confirmed_at__month=month,
        sales_invoice__isnull=False,
    )
    refunds = sum((r.amount for r in refunds_qs), ZERO)

    profit = revenue - cogs - refunds

    return {
        "year": year,
        "month": month,
        "revenue": revenue,
        "cogs": cogs,
        "refunds": refunds,
        "profit": profit,
    }
