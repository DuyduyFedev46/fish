"""
Kịch bản gọi soạn sẵn (CS-18) và tra mã tem (CS-17) — 2026-09-28-cskh-xac-nhan-in-tem, Lô 5.
Tuân thủ:
- Bất biến 9: kịch bản không chứa dữ liệu cá nhân (chặn chuỗi số dài, BR-GH-19); `lookup` chỉ trả mã và trạng thái.
- Bất biến 1: không có tiền hay giá vốn.
- Không AI (X-AC5).
"""
import re

from django.db import transaction

from apps.common.audit import record_audit
from apps.common.exceptions import BusinessError
from apps.common.pii import has_long_digit_run
from apps.delivery.models import CallScript, DeliveryNote, LabelPrint

MAX_CONTENT_LENGTH = 2000
LABEL_CODE_RE = re.compile(r"^GH-[A-Z0-9-]{3,40}\.\d{1,3}$")


def _clean_content(content) -> str:
    text = (content or "").strip() if isinstance(content, str) else ""
    if not text:
        raise BusinessError("Nội dung kịch bản không được để trống.", code="INVALID_INPUT")
    if len(text) > MAX_CONTENT_LENGTH:
        raise BusinessError(f"Nội dung kịch bản tối đa {MAX_CONTENT_LENGTH} ký tự.", code="INVALID_INPUT")
    if has_long_digit_run(text):
        raise BusinessError("Không ghi số điện thoại hay số tài khoản vào kịch bản.", code="BR-GH-19")
    return text


@transaction.atomic
def create_script(*, actor, situation, content, is_active=True) -> CallScript:
    if situation not in CallScript.Situation.values:
        raise BusinessError("Tình huống không hợp lệ.", code="INVALID_INPUT")
    if not isinstance(is_active, bool):
        raise BusinessError("`is_active` phải là true hoặc false.", code="INVALID_INPUT")
    text = _clean_content(content)
    if CallScript.objects.filter(situation=situation).exists():
        raise BusinessError("Tình huống này đã có kịch bản, hãy sửa kịch bản cũ.", code="INVALID_INPUT")
    script = CallScript.objects.create(situation=situation, content=text, is_active=is_active, updated_by=actor)
    record_audit(
        "create_callscript", actor=actor, obj=script,
        changes={"situation": situation, "is_active": is_active},
    )
    return script


@transaction.atomic
def update_script(*, actor, script, content=None, is_active=None) -> CallScript:
    script = CallScript.objects.select_for_update().get(pk=script.pk)
    changes = {}
    if content is not None:
        text = _clean_content(content)
        if text != script.content:
            script.content = text
            changes["content_changed"] = True
    if is_active is not None:
        if not isinstance(is_active, bool):
            raise BusinessError("`is_active` phải là true hoặc false.", code="INVALID_INPUT")
        if is_active != script.is_active:
            changes["is_active"] = {"from": script.is_active, "to": is_active}
            script.is_active = is_active
    if changes:
        script.updated_by = actor
        script.save(update_fields=["content", "is_active", "updated_by", "updated_at"])
        record_audit("update_callscript", actor=actor, obj=script, changes=changes)
    return script


def scripts_for_note(note: DeliveryNote) -> list[CallScript]:
    """
    Kịch bản đang dùng hợp với phiếu (02b §4.6): FIRST_ORDER nếu khách chưa có đơn PROCESSING/COMPLETED nào khác,
    ngược lại RETURNING; COMBO nếu có dòng đơn có `bundle_snapshot`; luôn kèm GENERAL nếu bật.
    """
    from apps.sales.models import SalesOrder

    invoice = getattr(note, "sales_invoice", None)
    order = getattr(invoice, "sales_order", None) if invoice else None
    wanted = []
    if order:
        has_other = (
            SalesOrder.objects.filter(
                customer_id=order.customer_id,
                status__in=[SalesOrder.Status.PROCESSING, SalesOrder.Status.COMPLETED],
            )
            .exclude(pk=order.pk)
            .exists()
        )
        wanted.append(CallScript.Situation.RETURNING if has_other else CallScript.Situation.FIRST_ORDER)
        if any(line.bundle_snapshot for line in order.lines.all()):
            wanted.append(CallScript.Situation.COMBO)
    wanted.append(CallScript.Situation.GENERAL)
    by_situation = {s.situation: s for s in CallScript.objects.filter(situation__in=wanted, is_active=True)}
    return [by_situation[s] for s in wanted if s in by_situation]


def lookup_label(code: str) -> dict:
    """
    Tra mã tem (CS-17, BR-GH-16, BR-GH-07). Chỉ trả mã phiếu, trạng thái và số lần in: không tên, SĐT, địa chỉ, giá.
    """
    code = (code or "").strip()
    if not LABEL_CODE_RE.match(code):
        raise BusinessError("Mã tem không đúng định dạng.", code="INVALID_INPUT")
    note_code, print_part = code.rsplit(".", 1)
    print_no = int(print_part)
    note = DeliveryNote.objects.filter(code=note_code).first()
    prints = list(LabelPrint.objects.filter(note=note).order_by("print_no")) if note else []
    if not note or print_no not in {p.print_no for p in prints}:
        raise BusinessError("Không tìm thấy phiếu.", code="NOT_FOUND", status_code=404)

    if note.status == DeliveryNote.Status.CANCELLED:
        valid_print_no = None
        warning = "BR-GH-07"
    else:
        valid = [p.print_no for p in prints if p.superseded_at is None and p.voided_at is None]
        valid_print_no = max(valid) if valid else None
        warning = None if valid_print_no == print_no else "BR-GH-16"
    return {
        "note_id": note.pk,
        "status": note.status,
        "print_no": print_no,
        "valid_print_no": valid_print_no,
        "warning": warning,
    }
