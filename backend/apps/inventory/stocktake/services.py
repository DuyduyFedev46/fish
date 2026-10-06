"""
Kiểm kê định kỳ & hao hụt (P-09, BR-KK) — nhập số đếm theo lô rồi duyệt để điều chỉnh tồn.

B1 (ERP theo design, Lô 8): `create_reconciliation`, `replace_lines`, `update_reconciliation` ghi dòng số đếm khi phiếu còn
`DRAFT`; `submit_reconciliation` gửi duyệt (DRAFT → SUBMITTED); `apply_reconciliation` duyệt (chỉ phiếu SUBMITTED).
Duy chốt 02/10 (#6): bỏ BR-KK-02 và BR-KK-08, người có quyền duyệt tự duyệt được; AuditLog vẫn ghi từng người. `AuditLog.changes` chỉ chứa số dòng / tên trường, không chép
tên, ghi chú hay lý do của dòng.
"""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.common.ai_visibility import exclude_ai_audit_rows
from apps.common.audit import record_audit
from apps.common.exceptions import BusinessError, ConflictError
from apps.inventory.models import Batch, StockLedgerEntry, StockReconciliation, StockReconciliationLine
from apps.inventory.stock import services as stock

ZERO = Decimal("0")

RECON_NOT_DRAFT = "RECON_NOT_DRAFT"
RECON_NOT_SUBMITTED = "RECON_NOT_SUBMITTED"
RECON_LINE_INVALID = "RECON_LINE_INVALID"
STALE_STATE = "STALE_STATE"
MAX_LINES = 500  # chặn payload quá lớn
MAX_REASON_LENGTH = 500
LINES_AUDIT_ACTION = "update_reconciliation_lines"
RECON_EMPTY = "RECON_EMPTY"
RECON_STOCK_INSUFFICIENT = "RECON_STOCK_INSUFFICIENT"
UNEDITABLE_STATUSES = ("CANCELLED", "CLOSED")


def _line_error(index, message, *, code=RECON_LINE_INVALID):
    return BusinessError(f"Dòng {index + 1}: {message}", code=code, extra={"line_index": index})


def _prepare_lines(lines):
    """
    Kiểm danh sách dòng `{batch: id, counted_qty: Decimal, reason: str}` và dựng object dòng chưa lưu.

    Server tự chụp `system_qty = batch.qty_available` và tính `difference_qty` (BR-KK-01); client không quyết định.
    Lỗi trả `BusinessError` có `line_index` (đếm từ 0) để FE tô đúng dòng.
    """
    if not isinstance(lines, (list, tuple)) or not lines:
        raise BusinessError("Cần ít nhất một dòng số đếm.", code=RECON_LINE_INVALID)
    if len(lines) > MAX_LINES:
        raise BusinessError(f"Tối đa {MAX_LINES} dòng mỗi phiếu.", code=RECON_LINE_INVALID)

    seen = set()
    for index, row in enumerate(lines):
        if row["batch"] in seen:
            raise _line_error(index, "lô này đã có ở dòng trên, mỗi lô chỉ đếm một lần.")
        seen.add(row["batch"])
    batches = Batch.objects.in_bulk(seen)

    prepared = []
    for index, row in enumerate(lines):
        batch = batches.get(row["batch"])
        if batch is None:
            raise _line_error(index, "không tìm thấy lô.")
        if batch.status in UNEDITABLE_STATUSES:
            raise _line_error(index, f"lô {batch.batch_id} đã huỷ hoặc đã chốt, không kiểm kê được.")
        counted = Decimal(row["counted_qty"])
        if counted < ZERO:
            raise _line_error(index, "số đếm phải từ 0 kg trở lên.")
        reason = (row.get("reason") or "").strip()
        if len(reason) > MAX_REASON_LENGTH:
            raise _line_error(index, f"lý do tối đa {MAX_REASON_LENGTH} ký tự.")
        difference = counted - batch.qty_available
        if difference > ZERO and not reason:
            raise _line_error(
                index, f"lô {batch.batch_id} đếm nhiều hơn sổ {difference} kg, cần ghi lý do (BR-KK-04).",
                code="BR-KK-04",
            )
        prepared.append(StockReconciliationLine(
            batch=batch, system_qty=batch.qty_available, counted_qty=counted,
            difference_qty=difference, reason=reason,
        ))
    return prepared


def _lock(reconciliation):
    return StockReconciliation.objects.select_for_update().get(pk=reconciliation.pk)


def _require_draft(reconciliation):
    if reconciliation.status != StockReconciliation.Status.DRAFT:
        raise BusinessError(
            "Phiếu kiểm kê đã gửi duyệt hoặc đã duyệt, không sửa dòng được (BR-PQ-10). "
            "Muốn sửa, hãy trả phiếu về nháp.",
            code=RECON_NOT_DRAFT,
        )


SYSTEM_NAME = "Hệ thống"


def staff_name(user):
    """Tên hiển thị của nhân viên: hồ sơ nhân viên, không có thì tên đăng nhập. Không bao giờ là SĐT."""
    if user is None:
        return SYSTEM_NAME
    profile = getattr(user, "staff_profile", None)
    return (profile.display_name if profile else "") or user.get_username()


def _last_editor_name(reconciliation):
    """Người thao tác gần nhất trên phiếu (từ AuditLog); chưa có dòng nhật ký thì lấy người tạo."""
    row = (
        exclude_ai_audit_rows(
            AuditLog.objects.filter(model_name=StockReconciliation._meta.label, object_id=str(reconciliation.pk))
        )
        .select_related("actor__staff_profile", "ai_actor__staff_profile")
        .order_by("-created_at", "-id").first()
    )
    if row is None:
        return staff_name(reconciliation.created_by)
    if row.actor_kind == AuditLog.ActorKind.AI:
        return f"AI của {staff_name(row.ai_actor)}"
    return staff_name(row.actor)


def _format_instant(value):
    from rest_framework.fields import DateTimeField

    return DateTimeField().to_representation(value)


@transaction.atomic
def create_reconciliation(*, count_date, note, lines, actor):
    """
    Tạo phiếu `DRAFT`. `lines` là danh sách đã parse (xem `_prepare_lines`) hoặc None (phiếu rỗng, điền sau).
    `actor` là người nhập số (ghi vào `created_by` và AuditLog).
    """
    prepared = _prepare_lines(lines) if lines is not None else []
    reconciliation = StockReconciliation.objects.create(count_date=count_date, note=note or "", created_by=actor)
    for item in prepared:
        item.reconciliation = reconciliation
    StockReconciliationLine.objects.bulk_create(prepared)
    record_audit(
        "create_stockreconciliation", actor=actor, obj=reconciliation, changes={"line_count": len(prepared)},
    )
    return reconciliation


@transaction.atomic
def replace_lines(*, reconciliation, lines, expected_updated_at, actor):
    """
    Thay TOÀN BỘ dòng số đếm của phiếu `DRAFT` (BR-KK-01).

    - Phiếu không còn `DRAFT` → 400 `RECON_NOT_DRAFT`.
    - `expected_updated_at` khác `updated_at` hiện tại → 409 `STALE_STATE` kèm `updated_at`, `updated_by_name`.
    - Dòng sai → 400 `RECON_LINE_INVALID`/`BR-KK-04`; dữ liệu cũ giữ nguyên (cả giao dịch rollback).
    Người gọi được ghi vào AuditLog (`update_reconciliation_lines`); không còn chặn tự duyệt (Duy chốt 02/10, #6).
    """
    locked = _lock(reconciliation)
    _require_draft(locked)
    if locked.updated_at is not None and expected_updated_at != locked.updated_at:
        raise ConflictError(
            "Phiếu vừa được người khác cập nhật, tải lại để xem.", code=STALE_STATE,
            extra={"updated_at": _format_instant(locked.updated_at), "updated_by_name": _last_editor_name(locked)},
        )
    prepared = _prepare_lines(lines)
    locked.lines.all().delete()
    for item in prepared:
        item.reconciliation = locked
    StockReconciliationLine.objects.bulk_create(prepared)
    locked.save(update_fields=["updated_at"])
    record_audit(LINES_AUDIT_ACTION, actor=actor, obj=locked, changes={"line_count": len(prepared)})
    reconciliation.updated_at = locked.updated_at
    return locked


@transaction.atomic
def update_reconciliation(*, reconciliation, changes, actor):
    """Sửa `note` / `count_date` của phiếu `DRAFT` (ED-27-AC3: phiếu đã duyệt → 400). Audit chỉ ghi tên trường."""
    locked = _lock(reconciliation)
    _require_draft(locked)
    fields = sorted(changes)
    for name in fields:
        setattr(locked, name, changes[name])
    locked.save(update_fields=[*fields, "updated_at"])
    record_audit("update_stockreconciliation", actor=actor, obj=locked, changes={"fields": fields})
    return locked


def _applied_difference(line):
    """
    BR-KK-09 (ĐỀ XUẤT, chờ Duy chốt): duyệt áp ĐÚNG chênh lệch đã chụp lúc nhập số (`counted_qty - system_qty`, bằng
    `difference_qty` với dòng qua service; dòng cũ tạo ngoài service có `difference_qty` mặc định 0 nên không dùng cột đó),
    không tính lại theo tồn hiện tại, để số người duyệt nhìn thấy bằng số vào sổ dù Shop có bán giữa chừng. Muốn đổi sang "tồn đã đổi thì
    409, bắt đếm lại" (Phương án A) thì chỉ sửa hàm này và `_apply_line`.
    """
    return line.counted_qty - line.system_qty


def _apply_line(reconciliation, line, *, index, approver):
    """Áp một dòng vào sổ kho. Lỗi gắn `line_index` để FE tô đúng dòng; cả phiếu rollback vì nằm trong giao dịch duyệt."""
    batch = line.batch
    diff = _applied_difference(line)
    if diff > ZERO and not line.reason:  # BR-KK-04 trên số đã chụp; dòng hợp lệ qua service luôn có lý do
        raise _line_error(
            index, f"lô {batch.batch_id} đếm nhiều hơn sổ, cần ghi lý do (BR-KK-04).", code="BR-KK-04",
        )
    if diff == ZERO:
        return
    try:
        stock.record_movement(
            batch=batch, qty_change=diff, movement_type=StockLedgerEntry.MovementType.RECONCILE,
            reference=f"reconciliation {reconciliation.pk}", actor=approver,
        )
    except BusinessError as error:
        raise _line_error(
            index, f"tồn lô {batch.batch_id} không đủ để áp chênh lệch đã đếm ({error}). Hãy đếm lại.",
            code=RECON_STOCK_INSUFFICIENT,
        ) from error


@transaction.atomic
def submit_reconciliation(*, reconciliation, actor):
    """Gửi duyệt: DRAFT → SUBMITTED (#20). Phiếu rỗng → `RECON_EMPTY`. Từ lúc này không sửa dòng, chỉ duyệt hoặc trả về nháp."""
    locked = _lock(reconciliation)
    _require_draft(locked)
    line_count = locked.lines.count()
    if not line_count:
        raise BusinessError("Phiếu chưa có dòng số đếm nào, không gửi duyệt được.", code=RECON_EMPTY)
    locked.status = StockReconciliation.Status.SUBMITTED
    locked.save(update_fields=["status", "updated_at"])
    record_audit("submit_stockreconciliation", actor=actor, obj=locked, changes={"line_count": line_count})
    return locked


@transaction.atomic
def return_to_draft(*, reconciliation, actor):
    """Trả phiếu đã gửi duyệt về nháp để sửa lại số đếm (#20). Chỉ từ SUBMITTED."""
    locked = _lock(reconciliation)
    if locked.status != StockReconciliation.Status.SUBMITTED:
        raise BusinessError("Chỉ trả về nháp được phiếu đang chờ duyệt.", code=RECON_NOT_SUBMITTED)
    locked.status = StockReconciliation.Status.DRAFT
    locked.save(update_fields=["status", "updated_at"])
    record_audit("return_stockreconciliation_to_draft", actor=actor, obj=locked, changes={})
    return locked


@transaction.atomic
def apply_reconciliation(*, reconciliation, approver):
    """
    Duyệt kiểm kê -> điều chỉnh tồn theo số thực đếm (BR-KK). Chỉ phiếu `SUBMITTED` (đã gửi duyệt) mới duyệt được.
    Duy chốt 02/10 (#6): bỏ BR-KK-02 và BR-KK-08; người có quyền duyệt tự duyệt phiếu mình nhập được.
    AuditLog giữ người nhập (`create_*`, `update_reconciliation_lines`), người gửi (`submit_*`) và người duyệt.
    BR-KK-09 (đề xuất): áp chênh lệch đã chụp lúc nhập số (xem `_applied_difference`). Phiếu không có dòng → `RECON_EMPTY`.
    Khoá dòng phiếu: hai người duyệt cùng lúc chỉ một người chạy.
    """
    _lock(reconciliation)
    reconciliation.refresh_from_db()  # trạng thái mới nhất sau khi giữ khoá
    if reconciliation.status == StockReconciliation.Status.APPROVED:
        raise BusinessError("Phiếu kiểm kê đã được duyệt.")
    if reconciliation.status != StockReconciliation.Status.SUBMITTED:
        raise BusinessError(
            "Phiếu kiểm kê chưa gửi duyệt. Hãy gửi duyệt trước khi duyệt.", code=RECON_NOT_SUBMITTED,
        )
    lines = list(reconciliation.lines.select_related("batch").order_by("id"))
    if not lines:
        raise BusinessError("Phiếu chưa có dòng số đếm nào, không duyệt được.", code=RECON_EMPTY)
    for index, line in enumerate(lines):
        _apply_line(reconciliation, line, index=index, approver=approver)
    line_count = len(lines)
    reconciliation.status = StockReconciliation.Status.APPROVED
    reconciliation.approved_by = approver
    reconciliation.approved_at = timezone.now()
    reconciliation.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
    record_audit(
        "approve_stockreconciliation", actor=approver, obj=reconciliation, changes={"line_count": line_count},
    )
    return reconciliation
