"""
Dịch vụ in tem giao hàng 100x150 mm (2026-09-28-cskh-xac-nhan-in-tem, CS-11).
Tuân thủ:
- Bất biến 1: Tuyệt đối không trả về hay lưu giá vốn, tiền, đơn giá
- Bất biến 9: SĐT trên tem chỉ ở dạng che (mask_phone_tail, chỉ 4 số cuối), mã barcode chỉ chứa mã phiếu và lần in
- Bất biến BR-GH-09 (chưa xác nhận không in tem), BR-GH-07 (đơn huỷ không in tem), BR-GH-16 (tem cũ không còn hiệu lực)
"""
import re

from django.db import transaction
from django.utils import timezone

from apps.common.audit import record_audit
from apps.common.exceptions import BusinessError
from apps.common.pii import mask_phone_tail
from apps.delivery.models import DeliveryNote, LabelPrint
from apps.sales.models.invoices import SalesInvoiceLineBatch

LABEL_CODE_RE = re.compile(r"^GH-[A-Z0-9-]{3,40}\.\d{1,3}$")


def get_label_data(note: DeliveryNote, print_no: int | None = None) -> dict:
    """
    Lấy dữ liệu hiển thị tem giao hàng (02b §4.3, CS-11).
    """
    if note.status == DeliveryNote.Status.CONFIRMING:
        raise BusinessError("Chưa xác nhận với khách, chưa in tem.", code="BR-GH-09")

    if note.status == DeliveryNote.Status.CANCELLED:
        raise BusinessError("Đơn đã huỷ, không in tem.", code="BR-GH-07")

    prints_qs = note.label_prints.all().order_by("print_no")
    max_print_no = prints_qs.values_list("print_no", flat=True).last() or 0
    next_print_no = max_print_no + 1

    is_reprint = False
    reprint_reason = None
    target_print_no = print_no

    if target_print_no is not None:
        target_print_no = int(target_print_no)
        lp = prints_qs.filter(print_no=target_print_no).first()
        if not lp:
            raise BusinessError(f"Không tìm thấy lượt in #{target_print_no}.", code="NOT_FOUND")
        if lp.superseded_at is not None or lp.voided_at is not None:
            raise BusinessError(f"Tem lần {target_print_no} không còn hiệu lực, dùng tem lần {next_print_no - 1}.", code="BR-GH-16")
        is_reprint = (target_print_no > 1)
        reprint_reason = lp.get_reason_display() if is_reprint else None
    else:
        # Xem trước: nếu đã từng in thì lấy lần in gần nhất còn hiệu lực
        valid_lp = prints_qs.filter(superseded_at__isnull=True, voided_at__isnull=True).last()
        if valid_lp:
            target_print_no = valid_lp.print_no
            is_reprint = (target_print_no > 1)
            reprint_reason = valid_lp.get_reason_display() if is_reprint else None
        else:
            target_print_no = 1
            is_reprint = False
            reprint_reason = None

    invoice = note.sales_invoice
    order = invoice.sales_order if invoice else None
    customer = order.customer if order else None

    # Tên và SĐT người nhận
    recipient_name = note.recipient_name or (customer.name if customer else "")
    raw_phone = note.recipient_phone or (order.phone if order else (customer.phone if customer else ""))
    recipient_phone_masked = mask_phone_tail(raw_phone)
    address = order.delivery_address if order else ""

    # Tính HSD sớm nhất và tổng kg từ allocations
    allocs = list(
        SalesInvoiceLineBatch.objects.filter(invoice_line__invoice=invoice)
        .select_related("component_item", "batch")
        .order_by("id")
    )
    total_kg_val = sum(float(a.qty) for a in allocs)
    total_kg = f"{total_kg_val:.3f}"

    expiry_dates = [a.batch.expiry_date for a in allocs if a.batch and a.batch.expiry_date]
    earliest_expiry = min(expiry_dates).isoformat() if expiry_dates else None

    return {
        "note_code": note.code,
        "order_code": order.code if order else "",
        "print_no": target_print_no,
        "next_print_no": next_print_no,
        "is_reprint": is_reprint,
        "reprint_reason": reprint_reason,
        "barcode_value": f"{note.code}.{target_print_no}",
        "recipient_name": recipient_name,
        "recipient_phone_masked": recipient_phone_masked,
        "address": address,
        "packages": "1/1",
        "total_kg": total_kg,
        "earliest_expiry": earliest_expiry,
        "paid_text": "ĐÃ THANH TOÁN – không thu thêm",
    }


def record_print(
    note: DeliveryNote,
    user,
    *,
    request_id=None,
    reason: str = LabelPrint.Reason.FIRST,
) -> tuple[LabelPrint, bool]:
    """
    Ghi nhận một lượt in tem giao hàng (idempotent theo request_id).
    """
    if note.status == DeliveryNote.Status.CONFIRMING:
        raise BusinessError("Chưa xác nhận với khách, chưa in tem.", code="BR-GH-09")

    if note.status == DeliveryNote.Status.CANCELLED:
        raise BusinessError("Đơn đã huỷ, không in tem.", code="BR-GH-07")

    if request_id:
        existing = LabelPrint.objects.filter(request_id=request_id).first()
        if existing:
            if existing.note_id == note.pk:
                return existing, True
            raise BusinessError("request_id đã tồn tại cho phiếu khác.", code="BR-GH-12")

    with transaction.atomic():
        locked_note = DeliveryNote.objects.select_for_update().get(pk=note.pk)
        if locked_note.status == DeliveryNote.Status.CANCELLED:
            raise BusinessError("Đơn đã huỷ, không in tem.", code="BR-GH-07")

        last_print = locked_note.label_prints.select_for_update().order_by("-print_no").first()
        next_print_no = (last_print.print_no + 1) if last_print else 1

        now = timezone.now()
        if next_print_no > 1:
            # Tem cũ trước đó bị vô hiệu (CS-14, 02b §2.4, §4.5)
            locked_note.label_prints.filter(superseded_at__isnull=True).update(superseded_at=now)

        actual_reason = LabelPrint.Reason.FIRST if next_print_no == 1 else LabelPrint.Reason.REPRINT
        if reason and reason in LabelPrint.Reason.values:
            actual_reason = reason

        lp = LabelPrint.objects.create(
            note=locked_note,
            print_no=next_print_no,
            reason=actual_reason,
            printed_by=user,
            request_id=request_id,
        )

        audit_action = "label_printed" if next_print_no == 1 else "label_reprinted"
        record_audit(
            audit_action,
            actor=user,
            obj=locked_note,
            changes={"print_no": next_print_no, "reason": actual_reason},
        )

        return lp, False


def void_label(note: DeliveryNote, user, print_no: int) -> dict:
    """
    Xác nhận đã huỷ tem giấy (CS-14, 02b §4.5).
    """
    if print_no is None:
        raise BusinessError("Thiếu print_no.", code="INVALID_INPUT")

    try:
        print_no = int(print_no)
    except (ValueError, TypeError):
        raise BusinessError("print_no không hợp lệ.", code="INVALID_INPUT")

    with transaction.atomic():
        locked_note = DeliveryNote.objects.select_for_update().get(pk=note.pk)
        lp = locked_note.label_prints.select_for_update().filter(print_no=print_no).first()
        if not lp:
            raise BusinessError(f"Không tìm thấy lượt in #{print_no}.", code="NOT_FOUND")

        if lp.voided_at is not None:
            return {
                "print_no": print_no,
                "voided_at": lp.voided_at.isoformat(),
                "already": True,
            }

        # Nếu đơn chưa huỷ và tem này đang là tem hiệu lực duy nhất (chưa superseded) -> không được huỷ (CS-14-AC4)
        if locked_note.status != DeliveryNote.Status.CANCELLED and lp.superseded_at is None:
            raise BusinessError(f"Tem lần {print_no} đang có hiệu lực, không huỷ được.", code="BR-GH-16")

        now = timezone.now()
        lp.voided_at = now
        lp.voided_by = user
        lp.save(update_fields=["voided_at", "voided_by"])

        record_audit(
            "label_voided",
            actor=user,
            obj=locked_note,
            changes={"print_no": print_no},
        )

        return {
            "print_no": print_no,
            "voided_at": now.isoformat(),
            "already": False,
        }


def lookup_label(code: str, *, queryset=None) -> dict:
    """
    Tra mã tem (CS-17, BR-GH-16, BR-GH-07). Chỉ trả mã phiếu, trạng thái và số lần in: không tên, SĐT, địa chỉ, giá.
    `queryset`: phạm vi dòng Tầng 3 của người gọi (None = mọi phiếu).
    """
    code = (code or "").strip()
    if not LABEL_CODE_RE.match(code):
        raise BusinessError("Mã tem không đúng định dạng.", code="INVALID_INPUT")
    note_code, print_part = code.rsplit(".", 1)
    print_no = int(print_part)
    note = (queryset if queryset is not None else DeliveryNote.objects).filter(code=note_code).first()
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
