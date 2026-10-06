"""
Luật "giao xong phiếu cuối thì đơn Hoàn tất" (W37 S1, BR-BH-18, BR-BH-21), dùng chung cho đường giao xong
(`delivery.services.advance_status`) và, về sau, lệnh chuyển bù (S3).

Quy ước khoá (BR-GH-24, 02b §1.3): mọi đường đổi phiếu giao khoá `SalesOrder` TRƯỚC rồi mới khoá `DeliveryNote`,
cùng thứ tự với `cancel_paid_order`, nên không có vòng chờ giữa huỷ đơn và giao xong.

Đơn chỉ đổi `status` (không động vào hoá đơn, kho, chứng từ đảo, phiếu hoàn: BR-BC-06). AuditLog của đơn do Hệ thống
ghi, `changes` có khoá cố định và KHÔNG chứa dữ liệu cá nhân của khách (bất biến 9).
"""
from apps.common.audit import record_audit
from apps.delivery.models import DeliveryNote
from apps.sales.models import SalesInvoice, SalesOrder

COMPLETE_ORDER_ACTION = "complete_order"  # AuditLog.action mới
BACKFILL_MARKER = "W37"  # đánh dấu dòng AuditLog do lệnh chuyển bù (S3) ghi

NoteStatus = DeliveryNote.Status


def is_delivery_finished(note_statuses) -> bool:
    """
    BR-BH-18: bỏ phiếu CANCELLED; còn ít nhất một phiếu và mọi phiếu còn lại đều COMPLETED.
    Hàm thuần, không truy vấn.
    """
    live = [status for status in note_statuses if status != NoteStatus.CANCELLED]
    return bool(live) and all(status == NoteStatus.COMPLETED for status in live)


def lock_order_of_note(note) -> SalesOrder | None:
    """
    Khoá dòng đơn của phiếu (gọi TRƯỚC khi khoá phiếu, trong `transaction.atomic`). Trả `None` khi phiếu không có đơn.
    Lấy `sales_order_id` qua hoá đơn không khoá (quan hệ hoá đơn -> đơn không đổi), rồi khoá đúng dòng đơn.
    Không dùng `select_for_update` kèm join để Postgres không khoá luôn dòng phiếu trước dòng đơn.
    """
    order_id = (
        SalesInvoice.objects.filter(pk=note.sales_invoice_id).values_list("sales_order_id", flat=True).first()
    )
    if order_id is None:
        return None
    return SalesOrder.objects.select_for_update().get(pk=order_id)


def complete_order_if_delivered(*, order, trigger_note, backfill=False) -> bool:
    """
    Gọi khi `order` ĐÃ KHOÁ. Chỉ đơn PROCESSING mới chuyển (BR-BH-21: PAID và COMPLETED giữ nguyên).
    Đọc trạng thái mọi phiếu của hoá đơn, áp `is_delivery_finished`, đổi đơn sang COMPLETED và ghi AuditLog
    `complete_order` (actor=None, Hệ thống). Trả True nếu đã chuyển.
    """
    if order is None or order.status != SalesOrder.Status.PROCESSING:
        return False
    invoice_id = SalesInvoice.objects.filter(sales_order_id=order.pk).values_list("pk", flat=True).first()
    if invoice_id is None:
        return False
    statuses = list(DeliveryNote.objects.filter(sales_invoice_id=invoice_id).values_list("status", flat=True))
    if not is_delivery_finished(statuses):
        return False

    old_status = order.status
    order.status = SalesOrder.Status.COMPLETED
    order.save(update_fields=["status"])
    changes = {
        "status": {"from": old_status, "to": order.status},
        "delivery_note": trigger_note.code,
        "delivery_note_id": trigger_note.pk,
    }
    if backfill:
        changes["backfill"] = BACKFILL_MARKER
    record_audit(COMPLETE_ORDER_ACTION, actor=None, obj=order, changes=changes)
    return True


def current_order_status(note):
    """Trạng thái đơn của phiếu, đọc mới từ DB (cho khoá `order_status` của API). None nếu không có hoá đơn/đơn."""
    return (
        SalesOrder.objects.filter(invoice__pk=note.sales_invoice_id).values_list("status", flat=True).first()
    )


def backfill_candidates():
    """S3: đơn PROCESSING có ít nhất một phiếu COMPLETED, không trùng, theo pk. Lọc thô; luật đầy đủ xét lại trong khoá."""
    return SalesOrder.objects.filter(
        status=SalesOrder.Status.PROCESSING,
        invoice__delivery_notes__status=NoteStatus.COMPLETED,
    ).distinct().order_by("pk")
