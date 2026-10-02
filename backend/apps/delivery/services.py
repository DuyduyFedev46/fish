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
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from apps.accounts import roles
from apps.common.audit import record_audit
from apps.common.exceptions import BusinessError, ConflictError
from apps.common.params import MAX_ID
from apps.common.pii import has_long_digit_run
from apps.inventory.models import ReturnToStock
from apps.sales.models import SalesInvoice

from .models import DeliveryNote

Status = DeliveryNote.Status
FailureReason = DeliveryNote.FailureReason

# BR-GH-23 (T6): chỉ giao / đổi người giao khi hàng chưa lên xe. DELIVERING và FAILED bị chặn vì hàng đang
# ở người giao cũ; COMPLETED, CANCELLED là điểm cuối.
ASSIGNABLE_STATUSES = frozenset({Status.CONFIRMING, Status.PREPARING, Status.READY})

# BR-GH-22: độ dài tối đa của ghi chú giao thất bại (khớp `DeliveryNote.failure_note`).
FAILURE_NOTE_MAX_LENGTH = 200

# Khác với None: client có gửi `expected_assigned_to` (kể cả null = "đang chưa có ai") thì mới kiểm.
NOT_CHECKED = object()

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
        elif to_status == Status.DELIVERING:  # #18: mốc bắt đầu giao (giao lại thì ghi đè)
            note.delivery_started_at = _now()
            update_fields.append("delivery_started_at")
        note.save(update_fields=update_fields)

    record_audit(
        "delivery_advance_status", actor=actor, obj=note,
        changes={"status": {"from": current, "to": to_status}},
    )
    return note, False


def _lock_note(note):
    """Khoá dòng phiếu rồi đồng bộ các trường trạng thái vào `note` (giữ nguyên prefetch của đối tượng gọi)."""
    locked = DeliveryNote.objects.select_for_update().get(pk=note.pk)
    for field in (
        "status", "failed_attempts", "assigned_to_id", "failure_reason", "failure_note", "completed_at",
        "delivery_started_at", "failed_at",
    ):
        setattr(note, field, getattr(locked, field))
    return note


def _clean_failure_input(reason, reason_note):
    """
    BR-GH-22: kiểm lý do và ghi chú giao thất bại. Trả (reason, note đã làm sạch).
    Thông điệp lỗi không lặp lại nội dung ghi chú (có thể chứa dữ liệu cá nhân, bất biến 9).
    """
    if not isinstance(reason, str) or reason not in FailureReason.values:
        raise BusinessError(
            "Chọn lý do giao thất bại.", code="DELIVERY_FAILURE_REASON_REQUIRED"
        )
    if reason_note is None:
        reason_note = ""
    if not isinstance(reason_note, str) or len(reason_note.strip()) > FAILURE_NOTE_MAX_LENGTH:
        raise BusinessError(
            f"Ghi chú tối đa {FAILURE_NOTE_MAX_LENGTH} ký tự.", code="DELIVERY_FAILURE_NOTE_INVALID"
        )
    reason_note = reason_note.strip()
    if reason == FailureReason.OTHER and not reason_note:
        raise BusinessError(
            "Chọn lý do Khác thì phải ghi chú.", code="DELIVERY_FAILURE_NOTE_REQUIRED"
        )
    if has_long_digit_run(reason_note):
        raise BusinessError(
            "Ghi chú không được chứa số điện thoại hay dãy số dài.", code="DELIVERY_FAILURE_NOTE_PII"
        )
    return reason, reason_note


def mark_failed(*, note, actor, reason=None, reason_note=""):
    """
    DELIVERING -> FAILED, failed_attempts += 1 (BR-GH-04). Sau khi vượt ngưỡng
    `settings.DELIVERY_MAX_FAILED_ATTEMPTS`, đánh dấu cần Quản lý/Chủ quyết định
    (E-08) — ngưỡng cấu hình được. FAILED có thể quay lại DELIVERING (hẹn giao
    lại) qua `advance_status`.

    BR-GH-22 (B5): `reason` thuộc `DeliveryNote.FailureReason`; "Khác" đòi `reason_note`. API luôn truyền
    `reason`, nên thiếu hoặc sai là 400. `reason=None` (không truyền) chỉ dành cho nơi gọi nội bộ cũ (job, test
    dữ liệu của lô khác): phiếu lưu lý do rỗng. Truyền `""` là thiếu lý do.
    Ghi chú là chữ tự do: chỉ lưu ở `failure_note`, KHÔNG vào AuditLog hay log (bất biến 9).
    """
    if reason is not None:
        reason, reason_note = _clean_failure_input(reason, reason_note)
    else:
        reason, reason_note = "", ""

    threshold = getattr(settings, "DELIVERY_MAX_FAILED_ATTEMPTS", 2)

    with transaction.atomic():
        _lock_note(note)  # đọc lại trạng thái trong khoá, tránh hai lần báo cùng lúc
        if note.status != Status.DELIVERING:
            raise BusinessError("Chỉ đánh dấu giao thất bại khi phiếu đang ở trạng thái Đang giao.")
        note.status = Status.FAILED
        note.failed_attempts += 1
        note.failure_reason = reason
        note.failure_note = reason_note
        note.failed_at = _now()  # #18
        note.save(update_fields=["status", "failed_attempts", "failure_reason", "failure_note", "failed_at"])

        needs_decision = note.failed_attempts >= threshold
        changes = {
            "failed_attempts": {"to": note.failed_attempts},
            "needs_decision": needs_decision,
        }
        if reason:
            changes["failure_reason"] = {"to": reason}
        record_audit(
            "delivery_mark_failed", actor=actor, obj=note,
            changes=changes,
            note="Vượt ngưỡng thất bại — cần Quản lý/Chủ quyết định (BR-GH-04)." if needs_decision else "",
        )
    return note, needs_decision


def staff_display_name(user) -> str:
    """Tên hiển thị của nhân viên (hồ sơ nhân sự), không có thì tên đăng nhập. Không bao giờ trả SĐT."""
    profile = getattr(user, "staff_profile", None)
    return (profile.display_name if profile else "") or user.get_username()


def list_deliverers():
    """
    BR-GH-23 / T7: người đang làm thuộc nhóm `delivery_staff`, kèm số phiếu `DELIVERING` và `READY` đang gán.
    Một truy vấn, không N+1.
    """
    User = get_user_model()
    return list(
        User.objects.filter(is_active=True, groups__name=roles.DELIVERY_STAFF)
        .select_related("staff_profile")
        .annotate(
            delivering_count=Count("deliveries", filter=Q(deliveries__status=Status.DELIVERING)),
            ready_count=Count("deliveries", filter=Q(deliveries__status=Status.READY)),
        )
        .order_by("staff_profile__display_name", "id")
    )


def resolve_assignee(raw_id):
    """Đổi `assigned_to` từ body thành User; sai kiểu hoặc không có thì 400 (chưa kiểm nhóm, việc của `assign_deliverer`)."""
    invalid = BusinessError(
        "Chọn người giao là nhân viên đang làm thuộc nhóm Nhân viên giao.", code="DELIVERY_ASSIGNEE_INVALID"
    )
    if isinstance(raw_id, bool) or not isinstance(raw_id, int) or not 1 <= raw_id <= MAX_ID:
        raise invalid
    user = get_user_model().objects.filter(pk=raw_id).first()
    if user is None:
        raise invalid
    return user


def validate_expected_assignee(raw):
    """`expected_assigned_to` trong body: null (chưa có ai) hoặc số nguyên dương trong int64. Sai kiểu là 400, không
    để rơi xuống phép so sánh sinh ra 409 giả."""
    if raw is None:
        return None
    if isinstance(raw, bool) or not isinstance(raw, int) or not 1 <= raw <= MAX_ID:
        raise BusinessError(
            "`expected_assigned_to` phải là số nguyên dương hoặc null.", code="DELIVERY_ASSIGNEE_INVALID"
        )
    return raw


def assign_deliverer(*, note, assignee, actor, expected_assignee_id=NOT_CHECKED):
    """
    BR-GH-23 (B6): giao hoặc đổi người giao. Trả (note, already).

    - Chỉ phiếu CONFIRMING / PREPARING / READY (`DELIVERY_ASSIGN_STATE`).
    - `assignee` phải đang làm (`is_active`) và thuộc `delivery_staff` (`DELIVERY_ASSIGNEE_INVALID`).
    - `expected_assignee_id` (kể cả None = chưa có ai) khác người đang gán => 409 `STALE_STATE`.
    - Gán đúng người đang gán => `already=True`, không ghi nhật ký.
    AuditLog chỉ ghi ID người cũ và mới, không ghi tên.
    """
    User = get_user_model()
    with transaction.atomic():
        _lock_note(note)
        if note.status not in ASSIGNABLE_STATUSES:
            raise BusinessError(
                f"Phiếu đang ở {note.get_status_display()}, không đổi người giao được.",
                code="DELIVERY_ASSIGN_STATE",
            )
        valid = assignee is not None and User.objects.filter(
            pk=assignee.pk, is_active=True, groups__name=roles.DELIVERY_STAFF
        ).exists()
        if not valid:
            raise BusinessError(
                "Người này không thuộc nhóm Nhân viên giao hoặc đã nghỉ.", code="DELIVERY_ASSIGNEE_INVALID"
            )
        if note.assigned_to_id == assignee.pk:
            return note, True
        if expected_assignee_id is not NOT_CHECKED and note.assigned_to_id != expected_assignee_id:
            raise ConflictError(
                "Phiếu vừa được giao cho người khác, tải lại để xem.",
                code="STALE_STATE",
                extra={"assigned_to": note.assigned_to_id},
            )
        old_id = note.assigned_to_id
        note.assigned_to = assignee
        note.save(update_fields=["assigned_to"])
        record_audit(
            "assign_deliverynote", actor=actor, obj=note,
            changes={"assigned_to": {"from": old_id, "to": assignee.pk}},
        )
    return note, False


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
