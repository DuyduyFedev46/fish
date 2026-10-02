"""
Tạo phiếu hàng hoàn từ phiếu giao (R9, 02b §3.8, BR-HV-01/02). Không đụng `services.apply_return` (duyệt).

Quy tắc (mã lỗi 400):
- `RETURN_NOTE_STATUS`: phiếu giao phải đang giao hoặc giao thất bại.
- `RETURN_BATCH_NOT_IN_NOTE`: lô phải thuộc phân bổ của hoá đơn của phiếu giao (BR-HV-01: về đúng lô gốc).
- `RETURN_QTY_EXCEEDS`: tổng số kg đã ghi nhận hoàn của (phiếu giao, lô), kể cả phiếu mới, không quá số kg đã giao của
  lô đó trên phiếu. Tính cả phiếu Chờ duyệt lẫn Đã duyệt. Khoá dòng phiếu giao trong lúc kiểm để hai yêu cầu cùng lúc
  không cùng lọt qua.
Việc tạo phiếu + ghi `AuditLog` `return_to_warehouse` dùng lại `delivery.services.return_to_warehouse`. Ghi chú tự do
chỉ nằm ở `ReturnToStock.note`, không vào AuditLog (bất biến 9).
"""
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from apps.common.exceptions import BusinessError
from apps.delivery import services as delivery_services
from apps.delivery.models import DeliveryNote
from apps.inventory.models import ReturnToStock
from apps.sales.models import SalesInvoiceLineBatch

ZERO = Decimal("0")
NOTE_STATUSES = (DeliveryNote.Status.FAILED, DeliveryNote.Status.DELIVERING)
DELIVERY_STARTED_ACTION = "delivery_advance_status"


def delivered_qty(delivery_note, batch):
    """Số kg của `batch` trên hoá đơn của phiếu giao (cộng mọi dòng phân bổ cùng lô)."""
    total = SalesInvoiceLineBatch.objects.filter(
        invoice_line__invoice_id=delivery_note.sales_invoice_id, batch=batch,
    ).aggregate(total=Sum("qty"))["total"]
    return total or ZERO


def returned_qty_by_batch(delivery_note, batch_ids=None):
    """Số kg đã ghi nhận hoàn của từng lô trên phiếu giao: {batch_pk: kg}, tính cả Chờ duyệt lẫn Đã duyệt.
    Một truy vấn gộp cho mọi lô. Dùng chung cho kiểm vượt số kg (`create_return`) và cho dòng phiếu giao (Lô 9)."""
    qs = ReturnToStock.objects.filter(delivery_note=delivery_note)
    if batch_ids is not None:
        qs = qs.filter(batch_id__in=batch_ids)
    return {row["batch_id"]: row["total"] or ZERO for row in qs.order_by().values("batch_id").annotate(total=Sum("qty"))}


def _left_warehouse_at(delivery_note):
    """Giờ rời kho = lần gần nhất phiếu chuyển sang ĐANG GIAO (theo AuditLog). Không có thì None."""
    from apps.accounts.models import AuditLog

    row = (
        AuditLog.objects.filter(
            model_name=DeliveryNote._meta.label, object_id=str(delivery_note.pk),
            action=DELIVERY_STARTED_ACTION, changes__status__to=DeliveryNote.Status.DELIVERING,
        )
        .order_by("-created_at", "-id")
        .first()
    )
    return row.created_at if row else None


@transaction.atomic
def create_return(*, delivery_note, batch, qty, actor, free_note=""):
    """Tạo phiếu hàng hoàn Chờ duyệt (decision=PENDING). Trả `ReturnToStock`."""
    locked = DeliveryNote.objects.select_for_update().get(pk=delivery_note.pk)
    if locked.status not in NOTE_STATUSES:
        raise BusinessError(
            "Chỉ ghi nhận hàng hoàn khi phiếu giao đang giao hoặc giao thất bại.", code="RETURN_NOTE_STATUS",
        )
    if batch.is_closed:
        # Lô đã chốt không nhận hàng hoàn (duyệt cũng bị chặn BR-HV-04) — chặn ngay khi tạo để phiếu không kẹt (QA Lô 9 B4).
        raise BusinessError("Lô đã chốt, không ghi nhận hàng hoàn vào lô này.", code="RETURN_BATCH_CLOSED")
    delivered = delivered_qty(locked, batch)
    if delivered <= ZERO:
        raise BusinessError(
            "Lô này không nằm trong phiếu giao, hàng hoàn phải về đúng lô gốc (BR-HV-01).",
            code="RETURN_BATCH_NOT_IN_NOTE",
        )
    already = returned_qty_by_batch(locked, [batch.pk]).get(batch.pk, ZERO)
    if already + qty > delivered:
        raise BusinessError(
            f"Số kg hoàn vượt số đã giao của lô: đã giao {delivered:f} kg, đã ghi nhận hoàn {already:f} kg.",
            code="RETURN_QTY_EXCEEDS",
            extra={"delivered_qty": f"{delivered:f}", "already_returned_qty": f"{already:f}"},
        )
    rt = delivery_services.return_to_warehouse(note=locked, batch=batch, qty=qty, actor=actor)
    rt.left_warehouse_at = _left_warehouse_at(locked)
    rt.note = free_note
    rt.save(update_fields=["left_warehouse_at", "note"])
    return rt
