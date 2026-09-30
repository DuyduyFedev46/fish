"""
Chứng từ đảo doanh thu (P8 Lô 4, F04, BR-HT-10) — append-only.

Huỷ đơn đã thanh toán thì doanh thu của hoá đơn phải đảo NGAY tại thời điểm huỷ, không chờ
phiếu hoàn (phiếu hoàn chỉ là dòng tiền). Chứng từ đảo ghi lại từng dòng lô gốc (qty, giá bán,
giá vốn đóng băng) để báo cáo lô/kỳ trừ đúng phần đã đảo. Hoá đơn gốc KHÔNG bị sửa (BR-HT-06).

Idempotent theo `source_key` ("cancel:<order.pk>"): gọi lại trả lại chứng từ cũ, không tạo thêm.
"""
from django.utils import timezone

from apps.common.audit import record_audit
from apps.common.exceptions import BusinessError

from apps.sales.models import SalesCreditNote, SalesCreditNoteLine, SalesInvoice


def issue_cancel_credit_note(*, invoice, actor, reason_code, stock_restored, at=None, backfilled=False):
    """
    Lập chứng từ đảo cho hoá đơn của đơn bị huỷ. Gọi TRONG transaction của cancel_paid_order
    (lỗi ở đây thì cả lần huỷ rollback). Trả SalesCreditNote (mới hoặc đã có).
    """
    order = invoice.sales_order
    source_key = f"cancel:{order.pk}"
    existing = SalesCreditNote.objects.filter(source_key=source_key).first()
    if existing is not None:
        return existing
    if invoice.status != SalesInvoice.Status.ISSUED:
        raise BusinessError(
            "Chỉ lập chứng từ đảo cho hoá đơn đang hiệu lực.", code="BR-HT-10",
        )

    cn = SalesCreditNote.objects.create(
        code=f"DC-{invoice.code}",
        source_key=source_key,
        kind=SalesCreditNote.Kind.CANCEL_ORDER,
        sales_invoice=invoice,
        issued_at=at or timezone.now(),
        amount=invoice.amount,
        stock_restored=stock_restored,
        reason_code=reason_code or "",
        backfilled=backfilled,
        created_by=actor,
    )
    for line in invoice.lines.all():
        for silb in line.batch_allocations.select_related("batch"):
            SalesCreditNoteLine.objects.create(
                credit_note=cn,
                invoice_line_batch=silb,
                batch=silb.batch,
                qty=silb.qty,
                rate=line.rate,
                amount=silb.qty * line.rate,
                unit_cost=silb.unit_cost,
            )
    record_audit(
        "issue_credit_note", actor=actor, obj=order,
        changes={"credit_note": cn.code, "amount": str(cn.amount), "backfilled": backfilled},
    )
    return cn
