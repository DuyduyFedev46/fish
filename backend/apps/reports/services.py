"""
Báo cáo giá vốn & lãi lỗ (P-10, mục 12 business-process-spec.md).

Hai góc nhìn (12.1):
- `batch_pnl`  : lãi/lỗ THEO LÔ — nguồn sự thật, tính lại từ `landed_unit_cost`
  hiện hành (BR-BC-04), không dùng số ảnh chụp trên đơn. Doanh thu chỉ tính hoá đơn
  chưa huỷ và TRỪ phần đã đảo bằng chứng từ đảo (BR-HT-10, P8 Lô 4). Chi phí chỉ gồm giá mua + phân bổ (hao hụt và hàng hỏng chỉ để hiển thị,
  không cộng hai lần vào giá vốn). Lô chưa `CLOSED` phải gắn nhãn "tạm tính" (BR-BC-05).
- `period_pnl` : lãi/lỗ THEO KỲ (tháng) — điều hành, doanh thu/giá vốn ghi nhận
  cùng thời điểm xác nhận thanh toán (BR-BC-01/02), hoàn tiền tính vào kỳ phát
  sinh hoàn, không sửa ngược kỳ cũ (BR-BC-03). Chứng từ đảo doanh thu (BR-HT-10) ghi vào
  kỳ HUỶ (issued_at của chứng từ), không sửa kỳ của hoá đơn gốc; phiếu hoàn xác nhận
  sau/cùng lúc huỷ không trừ lần hai (phiếu hoàn chỉ là dòng tiền), phiếu xác nhận trước huỷ vẫn ở kỳ của
  nó và số đảo = tiền hoá đơn − hoàn trước đó (D1-B, Duy quyết 30/09: không sửa kỳ cũ).

Không có bảng dữ liệu riêng — mọi thứ tính lại từ sales/inventory/purchasing.
"""
from decimal import Decimal

from apps.common.exceptions import BusinessError
from apps.inventory.models import Batch, ReturnToStock, StockLedgerEntry
from apps.sales.models import Refund, SalesCreditNote, SalesCreditNoteLine, SalesInvoice

ZERO = Decimal("0")


def batch_pnl(*, batch):
    """
    Lãi/lỗ theo lô (nguồn sự thật, BR-BC-04):
        Lãi/lỗ = doanh thu bán từ lô − (giá mua + chi phí phân bổ)

    - doanh thu bán từ lô = Σ(SalesInvoiceLineBatch.qty × rate dòng hoá đơn tương ứng),
      loại trừ hoá đơn đã huỷ (status=CANCELLED), TRỪ Σ dòng chứng từ đảo của lô
      (BR-HT-10: đơn huỷ sau thanh toán vẫn giữ hoá đơn ISSUED nhưng doanh thu đã đảo).
      Lô đã CLOSED chỉ trừ dòng chứng từ có issued_at <= closed_at (E2, Duy quyết 30/09: lô đã chốt
      không đổi số; chứng từ lập sau khi chốt chỉ vào kỳ hiện tại của `period_pnl`).
      `qty_sold` cũng trừ kg đã đảo; `reversed_qty`/`reversed_revenue` cho biết phần đã đảo.
    - giá mua = purchase_rate × qty_received (chưa gồm chi phí phụ).
    - chi phí phân bổ = Σ PurchaseCostAllocation.allocated_amount của lô.
    - hao hụt = kg âm từ kiểm kê (StockLedgerEntry.RECONCILE < 0) định giá theo
      landed_unit_cost HIỆN HÀNH (chỉ hiển thị số tiền mất, đã nằm trong giá mua,
      không cộng vào total_cost).
    - hàng hỏng = kg đã duyệt Huỷ bỏ (ReturnToStock.WRITE_OFF, APPROVED) định giá
      theo landed_unit_cost hiện hành (chỉ hiển thị số tiền mất, đã nằm trong giá mua,
      không cộng vào total_cost).
    - Lô chưa CLOSED -> "provisional": True (BR-BC-05, nhãn "tạm tính").
    """
    if batch is None:
        raise BusinessError("Thiếu lô để tính báo cáo lãi lỗ.")

    revenue = ZERO
    qty_sold = ZERO
    for alloc in batch.sold_allocations.select_related("invoice_line__invoice").exclude(
        invoice_line__invoice__status=SalesInvoice.Status.CANCELLED   # BR-BC-04 (L-11, Duy duyệt 28/09)
    ):
        revenue += alloc.qty * alloc.invoice_line.rate
        qty_sold += alloc.qty

    reversed_qty = ZERO
    reversed_revenue = ZERO
    credit_lines = SalesCreditNoteLine.objects.filter(
        batch=batch, credit_note__sales_invoice__status=SalesInvoice.Status.ISSUED,
    )
    if batch.status == Batch.Status.CLOSED and batch.closed_at is not None:
        # E2 (Duy quyết 30/09, BR-BC-04): lô đã chốt không đổi số — chứng từ lập SAU lúc chốt
        # (kể cả lập bù) không làm đổi lãi lỗ lô, chỉ vào period_pnl kỳ hiện tại.
        credit_lines = credit_lines.filter(credit_note__issued_at__lte=batch.closed_at)
    for cl in credit_lines:
        reversed_qty += cl.qty
        reversed_revenue += cl.amount
    revenue -= reversed_revenue
    qty_sold -= reversed_qty

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

    expired_qty = ZERO
    for entry in batch.ledger_entries.filter(
        movement_type=StockLedgerEntry.MovementType.WRITE_OFF, qty_change__lt=ZERO
    ):
        expired_qty += -entry.qty_change
    expired_cost = expired_qty * batch.landed_unit_cost

    # BR-BC-04 (sửa 2026-09-28, Duy duyệt, TL-4): purchase_cost đã tính trên toàn bộ qty_received, gồm cả kg hao hụt/hỏng/hết hạn
    # → shrinkage_cost/damage_cost/expired_cost chỉ để HIỂN THỊ số tiền mất, KHÔNG cộng vào total_cost.
    total_cost = purchase_cost + allocated_cost
    profit = revenue - total_cost

    return {
        "batch_id": batch.batch_id,
        "provisional": batch.status != Batch.Status.CLOSED,  # BR-BC-05
        "qty_received": batch.qty_received,
        "qty_sold": qty_sold,
        "landed_unit_cost": batch.landed_unit_cost,
        "revenue": revenue,
        "reversed_qty": reversed_qty,
        "reversed_revenue": reversed_revenue,
        "purchase_cost": purchase_cost,
        "allocated_cost": allocated_cost,
        "shrinkage_qty": shrinkage_qty,
        "shrinkage_cost": shrinkage_cost,
        "damage_qty": damage_qty,
        "damage_cost": damage_cost,
        "expired_qty": expired_qty,
        "expired_cost": expired_cost,
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
    - chứng từ đảo (BR-HT-10): doanh thu −= Σ SalesCreditNote.amount có issued_at thuộc tháng;
      (số đảo = cn.amount − Σ phiếu hoàn REFUNDED của hoá đơn xác nhận trước cn.issued_at, không âm);
      giá vốn −= Σ dòng chứng từ qty × unit_cost (ảnh chụp lúc bán; key `cogs_reversed`).
      Hoá đơn gốc ở kỳ cũ không bị sửa; kỳ huỷ có thể âm.
    - hoàn tiền: Σ Refund.amount có status=REFUNDED và confirmed_at thuộc tháng
      (BR-BC-03/BR-HT-06) — ghi vào kỳ phát sinh hoàn, không sửa ngược kỳ cũ. Chỉ phiếu
      gắn hoá đơn (S13-AC5), và
      KHÔNG tính phiếu xác nhận SAU/CÙNG lúc lập chứng từ đảo của hoá đơn đó (tránh trừ hai lần);
      phiếu xác nhận TRƯỚC khi huỷ vẫn trừ ở kỳ của nó (D1 phương án B, Duy quyết 30/09).
    """
    if not year or not month:
        raise BusinessError("Thiếu năm/tháng để tính báo cáo theo kỳ.")

    invoices = SalesInvoice.objects.filter(
        status=SalesInvoice.Status.ISSUED, issued_at__year=year, issued_at__month=month,
    )
    gross_revenue = sum((inv.amount for inv in invoices), ZERO)

    cogs = ZERO
    for inv in invoices.prefetch_related("lines__batch_allocations"):
        for line in inv.lines.all():
            for alloc in line.batch_allocations.all():
                cogs += alloc.qty * alloc.unit_cost

    credit_notes_qs = SalesCreditNote.objects.filter(
        issued_at__year=year, issued_at__month=month,
        sales_invoice__status=SalesInvoice.Status.ISSUED,
    ).select_related("sales_invoice")
    # D1 phương án B (Duy quyết 30/09, BR-HT-06): KHÔNG sửa kỳ cũ. Phiếu hoàn REFUNDED đã xác nhận
    # TRƯỚC lúc lập chứng từ đã trừ vào kỳ xác nhận của nó, nên số đảo doanh thu ở kỳ lập chứng từ
    # chỉ là phần còn lại: cn.amount − Σ hoàn trước đó (không âm).
    credit_notes = ZERO
    for cn in credit_notes_qs:
        refunded_before = sum(
            (r.amount for r in Refund.objects.filter(
                sales_invoice=cn.sales_invoice, status=Refund.Status.REFUNDED,
                confirmed_at__lt=cn.issued_at,
            )),
            ZERO,
        )
        credit_notes += max(ZERO, cn.amount - refunded_before)
    cogs_reversed = ZERO
    for cl in SalesCreditNoteLine.objects.filter(credit_note__in=credit_notes_qs):
        cogs_reversed += cl.qty * cl.unit_cost
    revenue = gross_revenue - credit_notes
    cogs -= cogs_reversed

    # S13-AC5: phiếu hoàn gắn giao dịch KHÔNG có hoá đơn (tiền về sau huỷ / thiếu / thừa) chưa
    # từng ghi doanh thu (BR-TT-06) → không trừ vào lãi kỳ; chỉ trả lại tiền khách.
    # Phiếu của hoá đơn đã có chứng từ đảo chỉ bị loại nếu xác nhận SAU/CÙNG lúc lập chứng từ
    # (đã đảo bằng chứng từ, không trừ hai lần); xác nhận trước thì vẫn trừ ở kỳ của nó (D1-B).
    refunds_qs = Refund.objects.filter(
        status=Refund.Status.REFUNDED, confirmed_at__year=year, confirmed_at__month=month,
        sales_invoice__isnull=False,
    )
    refunds = ZERO
    for r in refunds_qs.select_related("sales_invoice"):
        cn_at = (
            SalesCreditNote.objects.filter(sales_invoice_id=r.sales_invoice_id)
            .values_list("issued_at", flat=True).first()
        )
        if cn_at is not None and r.confirmed_at >= cn_at:
            continue
        refunds += r.amount

    profit = revenue - cogs - refunds

    return {
        "year": year,
        "month": month,
        "revenue": revenue,
        "cogs": cogs,
        "credit_notes": credit_notes,
        "cogs_reversed": cogs_reversed,
        "refunds": refunds,
        "profit": profit,
    }
