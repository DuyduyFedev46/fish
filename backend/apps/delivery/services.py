"""
Business logic soạn hàng & giao hàng (P-06) và hàng giao thất bại về kho (P-08).

State machine (mục 8, business-process-spec.md):
    PREPARING -> READY -> DELIVERING -> COMPLETED
    DELIVERING -> FAILED -> DELIVERING (hẹn giao lại)
COMPLETED là điểm KHÔNG quay lui (BR-GH-05) — mọi xử lý sau đó phải qua phiếu
hoàn tiền (P-07), không sửa lại phiếu giao.

`return_to_warehouse` chỉ TẠO phiếu hàng hoàn ở trạng thái chờ duyệt — nhân viên
giao hàng KHÔNG được tự nhập lại kho (BR-HV-02). Việc duyệt (RESTOCK/WRITE_OFF)
là `apps.inventory.returns.services.apply_return`, không làm ở đây.
"""
from uuid import uuid4

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.common.audit import record_audit
from apps.common.exceptions import BusinessError
from apps.inventory.models import ReturnToStock
from apps.sales.models import SalesInvoice

from .models import DeliveryNote

Status = DeliveryNote.Status

# BR-GH-05: COMPLETED không có cạnh đi ra (điểm không quay lui).
ALLOWED_TRANSITIONS = {
    Status.CONFIRMING: set(),
    Status.PREPARING: {Status.READY},
    Status.READY: {Status.DELIVERING},
    Status.DELIVERING: {Status.COMPLETED, Status.FAILED},
    Status.FAILED: {Status.DELIVERING},  # hẹn giao lại
    Status.COMPLETED: set(),
    Status.CANCELLED: set(),
}


def _now():
    return timezone.now()


def create_delivery_note(*, invoice, assigned_to=None, note="", status=None):
    """
    Tạo phiếu giao hàng cho một hoá đơn đã xuất (đơn đã thanh toán, PAID/PROCESSING).
    status khởi tạo = PREPARING (soạn hàng) mặc định; Lô 2 CSKH truyền CONFIRMING.
    Mã phiếu sinh duy nhất.
    """
    if invoice is None:
        raise BusinessError("Thiếu hoá đơn để tạo phiếu giao hàng.")
    if invoice.status != SalesInvoice.Status.ISSUED:
        raise BusinessError(
            "Chỉ tạo phiếu giao cho hoá đơn đã xuất (đơn đã thanh toán/đang xử lý)."
        )

    code = f"GH-{invoice.code}-{uuid4().hex[:5].upper()}"
    while DeliveryNote.objects.filter(code=code).exists():
        code = f"GH-{invoice.code}-{uuid4().hex[:5].upper()}"

    initial_status = status or Status.PREPARING
    with transaction.atomic():
        dn = DeliveryNote.objects.create(
            code=code,
            sales_invoice=invoice,
            status=initial_status,
            assigned_to=assigned_to,
            note=note,
        )
    return dn


def advance_status(*, note, to_status, actor, from_status=None):
    """
    Chuyển trạng thái phiếu giao đúng theo state machine P-06.
    Hỗ trợ from_status để kiểm tra stale state hoặc idempotency (already: True).
    Trả về (note, already: bool).
    """
    if to_status not in Status.values:
        raise BusinessError(f"Trạng thái '{to_status}' không hợp lệ.")

    current = note.status
    if current == Status.CONFIRMING:
        raise BusinessError("Chưa xác nhận với khách, chưa soạn được.", code="BR-GH-11")

    if current == Status.CANCELLED:
        raise BusinessError("Đơn đã huỷ, không soạn.", code="BR-GH-07")

    if from_status is not None:
        if current == to_status:
            return note, True
        if current != from_status:
            raise BusinessError(
                f"Phiếu đang ở {note.get_status_display()}, tải lại để xem.",
                code="STALE_STATE",
                extra={"current_status": current},
            )

    if current == Status.COMPLETED:
        raise BusinessError("Phiếu giao đã Hoàn tất — không quay lui được (BR-GH-05).", code="BR-GH-05")

    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if to_status not in allowed:
        current_label = note.get_status_display()
        try:
            to_label = Status(to_status).label
        except ValueError:
            to_label = to_status
        raise BusinessError(
            f"Không chuyển được từ {current_label} sang {to_label}.",
            code="BR-GH-05",
        )

    with transaction.atomic():
        note.status = to_status
        update_fields = ["status"]
        if to_status == Status.COMPLETED:
            note.completed_at = _now()
            update_fields.append("completed_at")
        note.save(update_fields=update_fields)

    record_audit(
        "delivery_advance_status", actor=actor, obj=note,
        changes={"status": {"from": current, "to": to_status}},
    )
    return note, False


def mark_failed(*, note, actor):
    """
    DELIVERING -> FAILED, failed_attempts += 1 (BR-GH-04). Sau khi vượt ngưỡng
    `settings.DELIVERY_MAX_FAILED_ATTEMPTS`, đánh dấu cần Quản lý/Chủ quyết định
    (E-08) — ngưỡng cấu hình được. FAILED có thể quay lại DELIVERING (hẹn giao
    lại) qua `advance_status`.
    """
    if note.status != Status.DELIVERING:
        raise BusinessError("Chỉ đánh dấu giao thất bại khi phiếu đang ở trạng thái Đang giao.")

    threshold = getattr(settings, "DELIVERY_MAX_FAILED_ATTEMPTS", 2)

    with transaction.atomic():
        note.status = Status.FAILED
        note.failed_attempts += 1
        note.save(update_fields=["status", "failed_attempts"])

    needs_decision = note.failed_attempts >= threshold
    record_audit(
        "delivery_mark_failed", actor=actor, obj=note,
        changes={
            "failed_attempts": {"to": note.failed_attempts},
            "needs_decision": needs_decision,
        },
        note="Vượt ngưỡng thất bại — cần Quản lý/Chủ quyết định (BR-GH-04)." if needs_decision else "",
    )
    return note, needs_decision


def return_to_warehouse(*, note, batch, qty, actor):
    """
    NV giao ghi nhận hàng mang về kho (P-08) — chỉ TẠO phiếu hàng hoàn ở trạng
    thái chờ duyệt (decision=PENDING, status=DRAFT). Nhân viên KHÔNG tự nhập lại
    kho (BR-HV-02); về đúng lô gốc (BR-HV-01). Duyệt qua
    `apps.inventory.returns.services.apply_return`.
    """
    if note.status not in (Status.FAILED, Status.DELIVERING):
        raise BusinessError(
            "Chỉ ghi nhận hàng hoàn về kho khi phiếu đang giao hoặc giao thất bại."
        )
    if batch is None:
        raise BusinessError("Thiếu lô gốc để ghi nhận hàng hoàn (BR-HV-01).")
    if qty is None or qty <= 0:
        raise BusinessError("Số kg hàng hoàn phải lớn hơn 0.")

    with transaction.atomic():
        rt = ReturnToStock.objects.create(
            delivery_note=note,
            batch=batch,
            qty=qty,
            left_warehouse_at=None,
            returned_at=_now(),
            decision=ReturnToStock.Decision.PENDING,
            status=ReturnToStock.Status.DRAFT,
            created_by=actor,
        )
    record_audit("return_to_warehouse", actor=actor, obj=rt, note="Chờ duyệt (BR-HV-02).")
    return rt
