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
    Status.PREPARING: {Status.READY},
    Status.READY: {Status.DELIVERING},
    Status.DELIVERING: {Status.COMPLETED, Status.FAILED},
    Status.FAILED: {Status.DELIVERING},  # hẹn giao lại
    Status.COMPLETED: set(),
}


def _now():
    return timezone.now()


def create_delivery_note(*, invoice, assigned_to=None, note=""):
    """
    Tạo phiếu giao hàng cho một hoá đơn đã xuất (đơn đã thanh toán, PAID/PROCESSING).
    status khởi tạo = PREPARING (soạn hàng). Mã phiếu sinh duy nhất.
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

    with transaction.atomic():
        dn = DeliveryNote.objects.create(
            code=code,
            sales_invoice=invoice,
            status=Status.PREPARING,
            assigned_to=assigned_to,
            note=note,
        )
    return dn


def advance_status(*, note, to_status, actor):
    """
    Chuyển trạng thái phiếu giao đúng theo state machine P-06. Sai state machine
    hoặc chuyển ra khỏi COMPLETED -> BusinessError (BR-GH-05). Set completed_at
    khi chuyển sang COMPLETED.
    """
    if to_status not in Status.values:
        raise BusinessError(f"Trạng thái '{to_status}' không hợp lệ.")

    current = note.status
    if current == Status.COMPLETED:
        raise BusinessError("Phiếu giao đã Hoàn tất — không quay lui được (BR-GH-05).")

    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if to_status not in allowed:
        raise BusinessError(
            f"Không thể chuyển phiếu giao từ '{current}' sang '{to_status}'."
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
    return note


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
