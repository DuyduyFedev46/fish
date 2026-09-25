"""
Thanh toán (P-05): ghi nhận tiền vào + xuất hoá đơn (chuyển giữ chỗ -> bán thật).

- confirm_payment: BR-TT-03 idempotent theo bank_txn_id; BR-TT-04 UNDERPAID; BR-TT-05
                   ORPHAN; khớp đủ -> issue_invoice + PROCESSING.
- issue_invoice  : release + SALE; BR-TT-06 ghi doanh thu tại issued_at; BR-BH-06
                   SalesInvoiceLineBatch là NGUỒN giá vốn. KHÔNG tạo DeliveryNote
                   (delivery tự bắt qua signal).
"""
from decimal import Decimal

from django.db import transaction

from apps.inventory.batches import services as batches
from apps.inventory.models import Batch, StockLedgerEntry
from apps.inventory.stock import services as stock
from apps.sales.models import (
    PaymentTransaction,
    SalesInvoice,
    SalesInvoiceLine,
    SalesInvoiceLineBatch,
    SalesOrder,
)
from apps.sales.utils import gen_code as _gen_code


# --- P-05: xác nhận thanh toán ----------------------------------------------

def confirm_payment(*, order, bank_txn_id, amount, received_at, source="WEBHOOK",
                    raw_payload=None, actor=None, invoice_code=None):
    """
    Ghi nhận tiền vào. IDEMPOTENT theo bank_txn_id (BR-TT-03) — gọi lại cùng mã GD trả
    lại đúng bản ghi cũ, KHÔNG trừ kho / xuất hoá đơn lần hai.

    - Đơn đã huỷ/hết hạn -> ORPHAN, chờ Chủ (BR-TT-05).
    - Tiền < tổng đơn     -> UNDERPAID, không xác nhận (BR-TT-04).
    - Khớp đủ             -> issue_invoice + order PAID->PROCESSING.

    `invoice_code`: mã hoá đơn chỉ định (chỉ seed_demo dùng để giữ mã demo ổn định);
    mặc định Hệ thống tự sinh.
    """
    amount = Decimal(str(amount))
    with transaction.atomic():
        # BR-TT-03: khoá chống trùng bằng mã giao dịch ngân hàng.
        existing = PaymentTransaction.objects.filter(bank_txn_id=bank_txn_id).first()
        if existing is not None:
            return existing

        o = SalesOrder.objects.select_for_update().get(pk=order.pk)

        if o.status in (SalesOrder.Status.CANCELLED, SalesOrder.Status.AUTO_CANCELLED):
            match_status = PaymentTransaction.MatchStatus.ORPHAN  # BR-TT-05
        elif o.status != SalesOrder.Status.BOOKED:
            # Đơn đã được xác nhận trước đó bằng giao dịch khác — coi như đã khớp, không xử lại.
            match_status = PaymentTransaction.MatchStatus.MATCHED
        elif amount < o.total_amount:
            match_status = PaymentTransaction.MatchStatus.UNDERPAID  # BR-TT-04
        else:
            match_status = PaymentTransaction.MatchStatus.MATCHED

        payment = PaymentTransaction.objects.create(
            bank_txn_id=bank_txn_id,
            sales_order=o,
            amount=amount,
            match_status=match_status,
            source=source,
            raw_payload=raw_payload or {},
            received_at=received_at,
        )

        # Chỉ chuyển tồn thành bán thật khi khớp đủ & đơn còn ở BOOKED.
        if match_status == PaymentTransaction.MatchStatus.MATCHED and (
            o.status == SalesOrder.Status.BOOKED
        ):
            issue_invoice(order=o, txn_ref=bank_txn_id, issued_at=received_at,
                          code=invoice_code)
            o.status = SalesOrder.Status.PROCESSING  # PAID -> PROCESSING
            o.save(update_fields=["status"])

    return payment


# --- P-05: xuất hoá đơn (chuyển giữ chỗ -> bán thật) ------------------------

def issue_invoice(*, order, txn_ref, issued_at, code=None):
    """
    Chuyển reservation thành tồn bán thật và ghi doanh thu (BR-TT-06 tại issued_at).
    Với mỗi SalesOrderLineBatch: release(qty) rồi record_movement SALE(-qty), sau đó
    tạo SalesInvoiceLineBatch với unit_cost = landed_unit_cost HIỆN HÀNH — đây là
    NGUỒN báo cáo giá vốn (BR-BH-06). KHÔNG tạo DeliveryNote ở đây.
    """
    with transaction.atomic():
        invoice = SalesInvoice.objects.create(
            code=code or _gen_code("INV", SalesInvoice),
            sales_order=order,
            customer=order.customer,
            issued_at=issued_at,
            amount=order.total_amount,
            payment_txn_ref=txn_ref or "",
            status=SalesInvoice.Status.ISSUED,
        )
        for line in order.lines.all():
            inv_line = SalesInvoiceLine.objects.create(
                invoice=invoice,
                item=line.item,
                qty=line.qty,
                rate=line.rate,
                amount=line.amount,
            )
            for res in line.batch_allocations.select_related("batch"):
                batches.release(batch=res.batch, qty=res.qty)
                stock.record_movement(
                    batch=res.batch,
                    qty_change=-res.qty,
                    movement_type=StockLedgerEntry.MovementType.SALE,
                    reference=invoice.code,
                    actor=None,
                )
                fresh = Batch.objects.get(pk=res.batch_id)  # landed_unit_cost hiện hành
                SalesInvoiceLineBatch.objects.create(
                    invoice_line=inv_line,
                    batch=res.batch,
                    component_item=res.component_item,
                    qty=res.qty,
                    unit_cost=fresh.landed_unit_cost,
                )
    return invoice
