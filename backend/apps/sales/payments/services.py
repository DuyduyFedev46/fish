"""
Thanh toán (P-05): ghi nhận tiền vào + xuất hoá đơn (chuyển giữ chỗ -> bán thật).

- confirm_payment: BR-TT-03 idempotent theo bank_txn_id; BR-TT-04 UNDERPAID; BR-TT-05
                   ORPHAN; khớp đủ -> issue_invoice + PROCESSING.
- confirm_payment_manual: S11 / BR-TT-08 — Chủ xác nhận tay trên ĐƠN, cùng lõi
                   `_record_payment` với webhook, + AuditLog actor (BR-PQ-04).
- issue_invoice  : release + SALE; BR-TT-06 ghi doanh thu tại issued_at; BR-BH-06
                   SalesInvoiceLineBatch là NGUỒN giá vốn. KHÔNG tạo DeliveryNote
                   (delivery tự bắt qua signal).
"""
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.common.audit import record_audit
from apps.common.exceptions import BusinessError

from apps.inventory.batches import services as batches
from apps.inventory.models import Batch, StockLedgerEntry
from apps.inventory.stock import services as stock
from apps.sales.models import (
    PaymentTransaction,
    SalesInvoice,
    SalesInvoiceLine,
    SalesInvoiceLineBatch,
    SalesOrder,
)
from apps.sales.utils import gen_code as _gen_code


# --- P-05: xác nhận thanh toán ----------------------------------------------

# BR-TT-08: xác nhận tay chỉ cho đơn Giữ chỗ (ghi nhận tiền) hoặc Tự huỷ (tiền về sau huỷ → ORPHAN).
MANUAL_CONFIRMABLE_STATUSES = (SalesOrder.Status.BOOKED, SalesOrder.Status.AUTO_CANCELLED)
MANUAL_CODE = "BR-TT-08"
BANK_TXN_ID_MAX_LENGTH = PaymentTransaction._meta.get_field("bank_txn_id").max_length  # 100


_AMOUNT_FIELD = PaymentTransaction._meta.get_field("amount")
AMOUNT_QUANT = Decimal(1).scaleb(-_AMOUNT_FIELD.decimal_places)  # 0.01 VND
# Miền cột amount (max_digits=14, decimal_places=2) → tối đa 999.999.999.999,99.
AMOUNT_MAX = Decimal(10) ** (_AMOUNT_FIELD.max_digits - _AMOUNT_FIELD.decimal_places) - AMOUNT_QUANT

AMOUNT_INVALID_MSG = "Số tiền phải là số lớn hơn 0."
AMOUNT_TOO_LARGE_MSG = "Số tiền quá lớn (tối đa 999.999.999.999,99 ₫)."


def normalize_bank_txn_id(raw):
    """
    B12 / BR-TT-03: dạng chuẩn của mã giao dịch ngân hàng — bỏ MỌI khoảng trắng, viết hoa.
    Dùng chung cho webhook (adapter đã gửi referenceCode FT…) và xác nhận tay, để cùng một
    khoản không bị ghi 2 lần chỉ vì khác hoa thường/khoảng trắng. Rỗng → "".
    """
    if raw is None:
        return ""
    return "".join(str(raw).split()).upper()


def validate_amount(raw):
    """
    B13 / BR-TT-08: số tiền hợp lệ → Decimal làm tròn về 0,01 VND (ROUND_HALF_UP).
    Sai → ValueError(thông điệp tiếng Việt): không phải số hữu hạn, ≤ 0 SAU làm tròn,
    hoặc vượt miền cột `amount`. Không bao giờ để lỗi Decimal rơi thành 500.
    """
    if raw is None or isinstance(raw, (bool, list, dict)):
        raise ValueError(AMOUNT_INVALID_MSG)
    try:
        amount = Decimal(str(raw).strip())
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(AMOUNT_INVALID_MSG) from None
    if not amount.is_finite() or amount <= 0:
        raise ValueError(AMOUNT_INVALID_MSG)
    if amount > AMOUNT_MAX + AMOUNT_QUANT:  # chặn sớm số khổng lồ trước khi quantize
        raise ValueError(AMOUNT_TOO_LARGE_MSG)
    amount = amount.quantize(AMOUNT_QUANT, rounding=ROUND_HALF_UP)
    if amount <= 0:
        raise ValueError(AMOUNT_INVALID_MSG)
    if amount > AMOUNT_MAX:
        raise ValueError(AMOUNT_TOO_LARGE_MSG)
    return amount


def parse_positive_amount(raw):
    """Như `validate_amount` nhưng sai → None (đường webhook trả WEBHOOK_INVALID_INPUT)."""
    try:
        return validate_amount(raw)
    except ValueError:
        return None


def confirm_payment(*, order, bank_txn_id, amount, received_at, source="WEBHOOK",
                    raw_payload=None, actor=None, invoice_code=None):
    """
    Ghi nhận tiền vào. IDEMPOTENT theo bank_txn_id (BR-TT-03) — gọi lại cùng mã GD trả
    lại đúng bản ghi cũ, KHÔNG trừ kho / xuất hoá đơn lần hai.

    - Đơn đã huỷ/hết hạn -> ORPHAN, chờ Chủ (BR-TT-05).
    - Tiền < tổng đơn     -> UNDERPAID, không xác nhận (BR-TT-04).
    - Khớp đủ             -> issue_invoice + order PAID->PROCESSING.

    `invoice_code`: mã hoá đơn chỉ định (chỉ seed_demo dùng để giữ mã demo ổn định);
    mặc định Hệ thống tự sinh.
    """
    payment, _created = _record_payment(
        order=order, bank_txn_id=bank_txn_id, amount=amount, received_at=received_at,
        source=source, raw_payload=raw_payload, actor=actor, invoice_code=invoice_code,
    )
    return payment


def confirm_payment_manual(*, order, bank_txn_id, amount=None, actor, received_at=None):
    """
    S11 / BR-TT-08: Chủ xác nhận "đã nhận tiền" trên ĐƠN (E-05, webhook không về).
    Chạy CHUNG `_record_payment` với webhook (đủ / thiếu / đơn đã tự huỷ / trùng mã GD),
    chỉ thêm: kiểm input, chỉ nhận đơn Giữ chỗ/Tự huỷ, source=MANUAL, AuditLog actor=Chủ.

    Trả `(payment, duplicate)`. Mã GD đã ghi cho CHÍNH đơn này → trả bản ghi cũ,
    duplicate=True (BR-TT-03); đã ghi cho đơn khác / chưa gắn đơn → BusinessError BR-TT-03.
    """
    bank_txn_id = normalize_bank_txn_id(bank_txn_id)  # B12: cùng hàm với webhook
    if not bank_txn_id:
        raise BusinessError("Thiếu mã giao dịch ngân hàng.", code=MANUAL_CODE)
    if len(bank_txn_id) > BANK_TXN_ID_MAX_LENGTH:
        raise BusinessError(
            f"Mã giao dịch ngân hàng dài quá {BANK_TXN_ID_MAX_LENGTH} ký tự.", code=MANUAL_CODE
        )
    if amount is None or (isinstance(amount, str) and not amount.strip()):
        amount = order.total_amount  # mặc định = tổng đơn (UC-03 bước 2)
    else:
        try:
            amount = validate_amount(amount)  # B13: làm tròn 0,01; ≤0 / quá lớn → 400
        except ValueError as exc:
            raise BusinessError(str(exc), code=MANUAL_CODE) from None

    payment, created = _record_payment(
        order=order, bank_txn_id=bank_txn_id, amount=amount,
        received_at=received_at or timezone.now(),
        source=PaymentTransaction.Source.MANUAL, actor=actor,
        allowed_statuses=MANUAL_CONFIRMABLE_STATUSES, audit_action="confirm_payment_manual",
    )
    if not created and payment.sales_order_id != order.pk:
        raise BusinessError(
            "Mã giao dịch này đã được ghi nhận cho giao dịch khác, không dùng lại (BR-TT-03).",
            code="BR-TT-03",
        )
    return payment, not created


def payment_outcome(payment):
    """
    Kết quả nghiệp vụ của một giao dịch (dùng cho phản hồi xác nhận tay, kể cả khi trùng).
    MATCHED → PAID (+ hoá đơn, phiếu giao); UNDERPAID → + đã trả / còn thiếu; còn lại → trạng thái đơn.
    """
    order = SalesOrder.objects.get(pk=payment.sales_order_id) if payment.sales_order_id else None
    status = PaymentTransaction.MatchStatus
    out = {"order_status": order.status if order else None}
    if payment.match_status == status.MATCHED:
        out["result"] = "PAID"
        invoice = SalesInvoice.objects.filter(sales_order=order).first() if order else None
        note = invoice.delivery_notes.order_by("-id").first() if invoice else None
        out["invoice_id"] = invoice.pk if invoice else None
        out["delivery_note_code"] = note.code if note else None
    elif payment.match_status == status.UNDERPAID:
        out["result"] = status.UNDERPAID
        paid_total = (
            order.payments.filter(match_status__in=(status.MATCHED, status.UNDERPAID))
            .aggregate(total=Sum("amount"))["total"] or Decimal("0")
        )
        out["paid_total"] = paid_total
        out["missing"] = max(order.total_amount - paid_total, Decimal("0"))
    else:
        out["result"] = payment.match_status
    return out


def _record_payment(*, order, bank_txn_id, amount, received_at, source, raw_payload=None,
                    actor=None, invoice_code=None, allowed_statuses=None, audit_action=None):
    """
    Lõi chung webhook + xác nhận tay. Trả `(payment, created)`.

    Khoá dòng đơn TRƯỚC khi kiểm trùng mã GD: hai lần bấm/webhook đồng thời cho cùng đơn
    xếp hàng tuần tự, lần sau thấy giao dịch lần trước (BR-TT-03).
    `allowed_statuses`: nhánh tay giới hạn trạng thái đơn (BR-TT-08), kiểm dưới khoá.
    """
    amount = Decimal(str(amount))
    bank_txn_id = normalize_bank_txn_id(bank_txn_id)  # B12: mọi đường ghi đều dạng chuẩn
    with transaction.atomic():
        o = SalesOrder.objects.select_for_update().get(pk=order.pk)

        # BR-TT-03: khoá chống trùng bằng mã giao dịch ngân hàng.
        existing = PaymentTransaction.objects.filter(bank_txn_id=bank_txn_id).first()
        if existing is not None:
            return existing, False

        if allowed_statuses is not None and o.status not in allowed_statuses:
            raise BusinessError("Đơn không ở trạng thái Giữ chỗ/Tự huỷ.", code=MANUAL_CODE)

        old_status = o.status
        if o.status in (SalesOrder.Status.CANCELLED, SalesOrder.Status.AUTO_CANCELLED):
            match_status = PaymentTransaction.MatchStatus.ORPHAN  # BR-TT-05
        elif o.status != SalesOrder.Status.BOOKED:
            # Đơn đã được xác nhận trước đó bằng giao dịch khác — coi như đã khớp, không xử lại.
            match_status = PaymentTransaction.MatchStatus.MATCHED
        elif amount < o.total_amount:
            match_status = PaymentTransaction.MatchStatus.UNDERPAID  # BR-TT-04
        else:
            match_status = PaymentTransaction.MatchStatus.MATCHED

        payment = PaymentTransaction.objects.create(
            bank_txn_id=bank_txn_id,
            sales_order=o,
            amount=amount,
            match_status=match_status,
            source=source,
            raw_payload=raw_payload or {},
            received_at=received_at,
        )

        # Chỉ chuyển tồn thành bán thật khi khớp đủ & đơn còn ở BOOKED.
        if match_status == PaymentTransaction.MatchStatus.MATCHED and (
            o.status == SalesOrder.Status.BOOKED
        ):
            issue_invoice(order=o, txn_ref=bank_txn_id, issued_at=received_at,
                          code=invoice_code)
            o.status = SalesOrder.Status.PROCESSING  # PAID -> PROCESSING
            o.save(update_fields=["status"])

        if audit_action:
            record_audit(
                audit_action, actor=actor, obj=o,
                changes={
                    "bank_txn_id": bank_txn_id,
                    "amount": amount,
                    "match_status": match_status,
                    "source": source,
                    "status": {"from": old_status, "to": o.status},
                },
            )

    return payment, True


# --- P-05: xuất hoá đơn (chuyển giữ chỗ -> bán thật) ------------------------

def issue_invoice(*, order, txn_ref, issued_at, code=None):
    """
    Chuyển reservation thành tồn bán thật và ghi doanh thu (BR-TT-06 tại issued_at).
    Với mỗi SalesOrderLineBatch: release(qty) rồi record_movement SALE(-qty), sau đó
    tạo SalesInvoiceLineBatch với unit_cost = landed_unit_cost HIỆN HÀNH — đây là
    NGUỒN báo cáo giá vốn (BR-BH-06). KHÔNG tạo DeliveryNote ở đây.
    """
    with transaction.atomic():
        invoice = SalesInvoice.objects.create(
            code=code or _gen_code("INV", SalesInvoice),
            sales_order=order,
            customer=order.customer,
            issued_at=issued_at,
            amount=order.total_amount,
            payment_txn_ref=txn_ref or "",
            status=SalesInvoice.Status.ISSUED,
        )
        for line in order.lines.all():
            inv_line = SalesInvoiceLine.objects.create(
                invoice=invoice,
                item=line.item,
                qty=line.qty,
                rate=line.rate,
                amount=line.amount,
            )
            for res in line.batch_allocations.select_related("batch"):
                batches.release(batch=res.batch, qty=res.qty)
                stock.record_movement(
                    batch=res.batch,
                    qty_change=-res.qty,
                    movement_type=StockLedgerEntry.MovementType.SALE,
                    reference=invoice.code,
                    actor=None,
                )
                fresh = Batch.objects.get(pk=res.batch_id)  # landed_unit_cost hiện hành
                SalesInvoiceLineBatch.objects.create(
                    invoice_line=inv_line,
                    batch=res.batch,
                    component_item=res.component_item,
                    qty=res.qty,
                    unit_cost=fresh.landed_unit_cost,
                )
    return invoice
