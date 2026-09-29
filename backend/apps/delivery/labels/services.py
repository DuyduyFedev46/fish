"""
Dịch vụ in tem giao hàng 100x150 mm (2026-09-28-cskh-xac-nhan-in-tem, CS-11).
Tuân thủ:
- Bất biến 1: Tuyệt đối không trả về hay lưu giá vốn, tiền, đơn giá
- Bất biến 9: SĐT trên tem chỉ ở dạng che (mask_phone), mã barcode chỉ chứa mã phiếu và lần in
- Bất biến BR-GH-09 (chưa xác nhận không in tem), BR-GH-07 (đơn huỷ không in tem), BR-GH-16 (tem cũ không còn hiệu lực)
"""
from django.db import transaction
from django.utils import timezone

from apps.common.audit import record_audit
from apps.common.exceptions import BusinessError
from apps.common.pii import mask_phone
from apps.delivery.models import DeliveryNote, LabelPrint
from apps.sales.models.invoices import SalesInvoiceLineBatch


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
    recipient_phone_masked = mask_phone(raw_phone)
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
