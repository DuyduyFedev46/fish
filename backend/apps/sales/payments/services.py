"""
Thanh toán (P-05): ghi nhận tiền vào + xuất hoá đơn (chuyển giữ chỗ -> bán thật).

- confirm_payment: BR-TT-03 idempotent theo bank_txn_id; BR-TT-04 UNDERPAID; BR-TT-05
                   ORPHAN; khớp đủ -> issue_invoice + PROCESSING.
- confirm_payment_manual: S11 / BR-TT-08 — Chủ xác nhận tay trên ĐƠN, cùng lõi
                   `_record_payment` với webhook, + AuditLog actor (BR-PQ-04).
- hàng chờ lệch  : S12 / BR-TT-09 — `resolve_payment` (gắn đơn / xác nhận khi khách đã bù),
                   `mark_payment_refunded` (S13: phiếu hoàn gắn giao dịch được xác nhận),
                   `payment_available_actions`. BR-TT-10 (P5): tiền về cho đơn đã thanh toán
                   → OVERPAID, vào hàng chờ để Chủ hoàn.
- issue_invoice  : release + SALE; BR-TT-06 ghi doanh thu tại issued_at; BR-BH-06
                   SalesInvoiceLineBatch là NGUỒN giá vốn. KHÔNG tạo DeliveryNote
                   (delivery tự bắt qua signal).
"""
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.conf import settings
from django.db import transaction
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
from apps.sales.utils import money_str, vnd_short


# --- P-05: xác nhận thanh toán ----------------------------------------------

# BR-TT-08: xác nhận tay chỉ cho đơn Giữ chỗ (ghi nhận tiền) hoặc Tự huỷ (tiền về sau huỷ → ORPHAN).
MANUAL_CONFIRMABLE_STATUSES = (SalesOrder.Status.BOOKED, SalesOrder.Status.AUTO_CANCELLED)
MANUAL_CODE = "BR-TT-08"
BANK_TXN_ID_MAX_LENGTH = PaymentTransaction._meta.get_field("bank_txn_id").max_length  # 100


_AMOUNT_FIELD = PaymentTransaction._meta.get_field("amount")
AMOUNT_QUANT = Decimal(1).scaleb(-_AMOUNT_FIELD.decimal_places)  # 0.01 VND
# Miền cột amount (max_digits=14, decimal_places=2) → tối đa 999.999.999.999,99.
AMOUNT_MAX = Decimal(10) ** (_AMOUNT_FIELD.max_digits - _AMOUNT_FIELD.decimal_places) - AMOUNT_QUANT

# Quyết định Duy 2026-09-26 (BR-TT-08): VND không có số lẻ → tối thiểu 1đ (so SAU làm tròn).
AMOUNT_MIN = Decimal("1")

AMOUNT_INVALID_MSG = "Số tiền phải là số lớn hơn 0."
AMOUNT_MIN_MSG = "Số tiền tối thiểu 1đ."
AMOUNT_TOO_LARGE_MSG = "Số tiền quá lớn (tối đa 999.999.999.999,99 ₫)."

# BR-TT-15 (UC-5, PA, quyết định Duy 2026-09-26): nhãn cảnh báo khi một khoản OVERPAID mới
# (mã giao dịch khác) trùng SỐ TIỀN với một khoản đã MATCHED qua xác nhận tay (MANUAL) của
# CHÍNH đơn đó — rất có thể là cùng một lần chuyển khoản, Chủ gõ tay rồi IPN mới báo về sau,
# KHÔNG PHẢI tiền thừa thật. Không tự hoàn khi thấy nhãn này — đối chiếu sao kê trước.
DUPLICATE_MANUAL_WARNING = "Nghi trùng xác nhận tay, đối chiếu sao kê trước khi hoàn"


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
    < 1đ sau làm tròn (L8, quyết định Duy 2026-09-26), hoặc vượt miền cột `amount`. Không bao giờ để lỗi Decimal rơi thành 500.
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
    if amount < AMOUNT_MIN:
        raise ValueError(AMOUNT_MIN_MSG)
    if amount > AMOUNT_MAX:
        raise ValueError(AMOUNT_TOO_LARGE_MSG)
    return amount


def environment_for_source(source):
    """
    BR-TT-14: chỉ giao dịch từ Cổng SePay (Source.GATEWAY) mới gắn môi trường — lấy từ
    `settings.SEPAY_ENV` TẠI THỜI ĐIỂM ghi (đây cũng là môi trường Django dùng để ký tham số
    thanh toán ở P1, nên luôn khớp). Webhook ngân hàng cũ / xác nhận tay không có khái niệm
    môi trường cổng → "".
    """
    if source != PaymentTransaction.Source.GATEWAY:
        return ""
    return (getattr(settings, "SEPAY_ENV", "") or "").strip().upper()


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
        extra = overpaid_amount(payment)
        if extra is not None:
            out["overpaid_amount"] = extra  # L8: phần thừa đã vào hàng chờ
    elif payment.match_status == status.UNDERPAID:
        out["result"] = status.UNDERPAID
        paid_total = order_paid_total(order)
        out["paid_total"] = paid_total
        out["missing"] = max(order.total_amount - paid_total, Decimal("0"))
    else:
        out["result"] = payment.match_status
    return out


def initial_resolution_status(match_status):
    """BR-TT-09: giao dịch lệch vào hàng chờ (OPEN) ngay khi ghi; khớp → null (không thuộc hàng chờ)."""
    if match_status == PaymentTransaction.MatchStatus.MATCHED:
        return None
    return PaymentTransaction.ResolutionStatus.OPEN


def _countable_payments(order):
    """
    Giao dịch tính vào "khách đã trả" của đơn (Q9): khớp hoặc thiếu, chưa bị hoàn / đang hoàn
    (phiếu hoàn chưa Thất bại gắn thẳng vào giao dịch, S13).
    """
    from apps.sales.models import Refund

    status = PaymentTransaction.MatchStatus
    refunding = Refund.objects.filter(
        payment_transaction__isnull=False,
        status__in=(Refund.Status.PENDING, Refund.Status.REFUNDED),
    ).values("payment_transaction")
    # Subquery thay cho join + DISTINCT: Postgres không cho SELECT DISTINCT … FOR UPDATE.
    return (
        order.payments.filter(match_status__in=(status.MATCHED, status.UNDERPAID))
        .exclude(resolution=PaymentTransaction.Resolution.REFUNDED)
        .exclude(pk__in=refunding)
    )


def order_paid_total(order):
    """Tổng khách đã trả cho đơn (dùng cho S11 `paid_total` và hàng chờ S12)."""
    return sum((p.amount for p in _countable_payments(order)), Decimal("0"))


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
            # BR-TT-10 (P5, N-6): đơn đã thanh toán bằng giao dịch khác → tiền chuyển thừa,
            # không xử lại đơn, vào hàng chờ để Chủ hoàn.
            match_status = PaymentTransaction.MatchStatus.OVERPAID
        elif amount < o.total_amount:
            match_status = PaymentTransaction.MatchStatus.UNDERPAID  # BR-TT-04
        else:
            match_status = PaymentTransaction.MatchStatus.MATCHED

        # BR-TT-10 (L8, quyết định Duy 2026-09-26): chuyển thừa ngay lần đầu → dòng khớp chỉ
        # mang đúng tổng đơn, phần thừa tách thành dòng OVERPAID riêng ngay dưới.
        matched_amount = amount
        if match_status == PaymentTransaction.MatchStatus.MATCHED:
            matched_amount = min(amount, o.total_amount)

        payment = PaymentTransaction.objects.create(
            bank_txn_id=bank_txn_id,
            sales_order=o,
            amount=matched_amount,
            match_status=match_status,
            resolution_status=initial_resolution_status(match_status),
            source=source,
            environment=environment_for_source(source),
            raw_payload=raw_payload or {},
            received_at=received_at,
        )

        # BR-TT-15 (UC-5): khoản OVERPAID này (mã GD khác) trùng số tiền với một khoản đã
        # MATCHED bằng xác nhận tay của CHÍNH đơn -> rất có thể là cùng một lần chuyển khoản,
        # không phải tiền thừa thật. Gắn nhãn để Chủ đối chiếu sao kê trước khi hoàn.
        if match_status == PaymentTransaction.MatchStatus.OVERPAID and source != PaymentTransaction.Source.MANUAL:
            manual_duplicate = o.payments.filter(
                source=PaymentTransaction.Source.MANUAL,
                match_status=PaymentTransaction.MatchStatus.MATCHED,
                amount=amount,
            ).exclude(pk=payment.pk).exists()
            if manual_duplicate:
                payment.duplicate_warning = DUPLICATE_MANUAL_WARNING
                payment.save(update_fields=["duplicate_warning"])

        # Chỉ chuyển tồn thành bán thật khi khớp đủ & đơn còn ở BOOKED.
        if match_status == PaymentTransaction.MatchStatus.MATCHED and (
            o.status == SalesOrder.Status.BOOKED
        ):
            issue_invoice(order=o, txn_ref=bank_txn_id, issued_at=received_at,
                          code=invoice_code)
            o.status = SalesOrder.Status.PROCESSING  # PAID -> PROCESSING
            o.save(update_fields=["status"])
            split_overpaid(payment=payment, order=o, bank_amount=amount, actor=actor)

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


# --- BR-TT-10 (L8): chuyển thừa ngay lần đầu → tách phần thừa vào hàng chờ -------

OVERPAID_SUFFIX = "-THUA"


def overpaid_split_id(bank_txn_id, n=1):
    """
    Mã của dòng phần thừa: `<mã GD>-THUA` (cắt bớt mã gốc nếu vượt 100 ký tự). `n` > 1 chỉ
    dùng khi mã đó đã bị chiếm (cực hiếm) → `-THUA2`, `-THUA3`… Tra ngược qua `split_from`.
    """
    suffix = OVERPAID_SUFFIX + (str(n) if n > 1 else "")
    return bank_txn_id[:BANK_TXN_ID_MAX_LENGTH - len(suffix)] + suffix


def split_overpaid(*, payment, order, bank_amount, actor=None):
    """
    BR-TT-10 mở rộng (quyết định Duy 2026-09-26): khoản `bank_amount` vừa làm đơn Giữ chỗ
    thành đã thanh toán nhưng LỚN HƠN tổng đơn → phần thừa thành một PaymentTransaction
    OVERPAID riêng, OPEN trong hàng chờ để Chủ hoàn (S12/S13). Dòng khớp (`payment`) mang
    đúng tổng đơn; hai dòng cộng lại = đúng số ngân hàng báo. Gọi trong transaction đang
    khoá dòng đơn; idempotent nhờ `_record_payment` trả bản ghi cũ khi trùng mã GD.
    Trả dòng phần thừa, hoặc None khi không thừa.
    """
    excess = bank_amount - order.total_amount
    if excess <= 0:
        return None
    n = 1
    while PaymentTransaction.objects.filter(bank_txn_id=overpaid_split_id(payment.bank_txn_id, n)).exists():
        n += 1
    extra = PaymentTransaction.objects.create(
        bank_txn_id=overpaid_split_id(payment.bank_txn_id, n),
        sales_order=order,
        amount=excess,
        match_status=PaymentTransaction.MatchStatus.OVERPAID,
        resolution_status=initial_resolution_status(PaymentTransaction.MatchStatus.OVERPAID),
        source=payment.source,
        environment=payment.environment,  # BR-TT-14: phần tách vẫn "từ cổng" như dòng gốc
        raw_payload={"split_from": payment.bank_txn_id, "bank_amount": str(bank_amount)},
        received_at=payment.received_at,
    )
    record_audit(
        "split_overpaid_payment", actor=actor, obj=extra,
        changes={
            "bank_txn_id": payment.bank_txn_id,
            "bank_amount": bank_amount,
            "order": order.code,
            "total_amount": order.total_amount,
            "overpaid_amount": excess,
        },
    )
    return extra


def overpaid_amount(payment):
    """Phần thừa đã tách từ giao dịch khớp `payment` (BR-TT-10 L8); không có → None."""
    if payment.match_status != PaymentTransaction.MatchStatus.MATCHED:
        return None
    extra = PaymentTransaction.objects.filter(
        sales_order_id=payment.sales_order_id,
        match_status=PaymentTransaction.MatchStatus.OVERPAID,
        raw_payload__split_from=payment.bank_txn_id,
    ).first()
    return extra.amount if extra else None


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


# --- S12: hàng chờ thanh toán lệch (BR-TT-09) ---------------------------------

RESOLVE_CODE = "BR-TT-09"
ORPHAN_CODE = "BR-TT-05"
RESOLVE_PERM = "sales.confirm_payment_manual"  # hàng chờ lệch là việc của Chủ (BR-TT-07)


class ResolveAction:
    ATTACH_TO_ORDER = "ATTACH_TO_ORDER"
    CONFIRM_ORDER = "CONFIRM_ORDER"
    ALL = (ATTACH_TO_ORDER, CONFIRM_ORDER)


def _confirmable_payments(order):
    """Giao dịch thiếu tiền còn mở của đơn, dùng để xác nhận theo TỔNG (Q9)."""
    return _countable_payments(order).filter(
        match_status=PaymentTransaction.MatchStatus.UNDERPAID,
        resolution_status=PaymentTransaction.ResolutionStatus.OPEN,
    ).order_by("received_at", "id")


def _check_order_bookable(order):
    """Chỉ đơn Giữ chỗ nhận tiền được; đơn đã huỷ → chỉ còn hoàn (BR-TT-05)."""
    if order.status == SalesOrder.Status.AUTO_CANCELLED:
        raise BusinessError("Đơn đã tự huỷ, chỉ còn cách hoàn tiền.", code=ORPHAN_CODE)
    if order.status == SalesOrder.Status.CANCELLED:
        raise BusinessError("Đơn đã huỷ, chỉ còn cách hoàn tiền.", code=ORPHAN_CODE)
    if order.status != SalesOrder.Status.BOOKED:
        raise BusinessError(
            "Đơn không ở trạng thái Giữ chỗ (đã thanh toán hoặc đang xử lý).", code=RESOLVE_CODE
        )


def payment_available_actions(*, payment, user):
    """
    Thao tác trên một dòng hàng chờ (quy ước `available_actions`: luật + quyền).
    - attach_to_order: giao dịch không khớp đơn, còn mở.
    - confirm_order  : giao dịch thiếu tiền còn mở, đơn Giữ chỗ, tổng đã trả ≥ tổng đơn (Q9).
    - refund         : còn mở, còn tiền hoàn được (BR-HT-04) + `create_refund` (S13-AC6).
    Mọi thao tác đòi `confirm_payment_manual` (chỉ Chủ).
    """
    from apps.sales.refunds.services import payment_refundable_amount

    if payment.resolution_status != PaymentTransaction.ResolutionStatus.OPEN:
        return []
    if not user.has_perm(RESOLVE_PERM):
        return []
    status = PaymentTransaction.MatchStatus
    actions = []
    order = payment.sales_order
    if payment.match_status == status.UNMATCHED and order is None:
        actions.append("attach_to_order")
    if (payment.match_status == status.UNDERPAID and order is not None
            and order.status == SalesOrder.Status.BOOKED
            and _confirmable_payments(order).filter(pk=payment.pk).exists()
            and order_paid_total(order) >= order.total_amount):
        actions.append("confirm_order")
    if (user.has_perm("sales.create_refund")
            and payment_refundable_amount(payment=payment) > 0):
        actions.append("refund")
    return actions


def resolve_payment(*, payment, action, actor, order_id=None, note=""):
    """
    S12 / BR-TT-09: Chủ đóng một giao dịch lệch. Hoàn tiền đi qua phiếu hoàn (S13).

    - ATTACH_TO_ORDER: giao dịch không khớp → gắn vào đơn Giữ chỗ. Đủ tiền (tính cả khoản
      thiếu đã có của đơn) → hoá đơn + PROCESSING như S11, giao dịch RESOLVED/ATTACHED.
      Chưa đủ → gắn đơn, thành UNDERPAID, vẫn OPEN chờ bù.
    - CONFIRM_ORDER : đơn Giữ chỗ có các khoản thiếu cộng lại ≥ tổng đơn → hoá đơn + PROCESSING,
      mọi khoản đó RESOLVED/CONFIRMED (Q9).

    Khoá theo thứ tự ĐƠN → GIAO DỊCH (cùng thứ tự với webhook `_record_payment`) rồi mới kiểm
    OPEN → bấm đúp lần hai nhận 400, không xử lý hai lần; hai giao dịch của cùng một đơn xác
    nhận đồng thời xếp hàng trên dòng đơn, không khoá chéo. Trả dict kết quả cho API.
    """
    action = str(action or "").strip().upper()
    if action not in ResolveAction.ALL:
        raise BusinessError(
            "Cách xử lý không hợp lệ: ATTACH_TO_ORDER hoặc CONFIRM_ORDER "
            "(hoàn tiền thì tạo phiếu hoàn).", code=RESOLVE_CODE,
        )
    note = str(note or "").strip()
    if action == ResolveAction.ATTACH_TO_ORDER:
        try:
            order_id = int(order_id)
        except (TypeError, ValueError):
            raise BusinessError("Thiếu hoặc sai order_id.", code=RESOLVE_CODE) from None

    with transaction.atomic():
        if action == ResolveAction.ATTACH_TO_ORDER:
            order_pk = order_id
        else:
            order_pk = (PaymentTransaction.objects.filter(pk=payment.pk)
                        .values_list("sales_order_id", flat=True).first())
        order = (SalesOrder.objects.select_for_update().filter(pk=order_pk).first()
                 if order_pk is not None else None)
        p = PaymentTransaction.objects.select_for_update().get(pk=payment.pk)
        if p.resolution_status == PaymentTransaction.ResolutionStatus.RESOLVED:
            raise BusinessError("Giao dịch đã được xử lý, không xử lý lại.", code=RESOLVE_CODE)
        if p.resolution_status != PaymentTransaction.ResolutionStatus.OPEN:
            raise BusinessError("Giao dịch đã khớp đơn, không thuộc hàng chờ.", code=RESOLVE_CODE)
        if action == ResolveAction.ATTACH_TO_ORDER:
            return _attach_to_order(p, order=order, actor=actor, note=note)
        if p.sales_order_id != order_pk:  # vừa bị gắn đơn bởi thao tác khác giữa hai lần đọc
            raise BusinessError("Giao dịch vừa thay đổi, tải lại hàng chờ.", code=RESOLVE_CODE)
        return _confirm_order(p, order=order, actor=actor, note=note)


def _attach_to_order(p, *, order, actor, note):
    status = PaymentTransaction.MatchStatus
    if p.sales_order_id is not None or p.match_status != status.UNMATCHED:
        raise BusinessError("Chỉ gắn đơn cho giao dịch không khớp đơn.", code=RESOLVE_CODE)
    if order is None:
        raise BusinessError("Không tìm thấy đơn để gắn.", code=RESOLVE_CODE)
    _check_order_bookable(order)

    p.sales_order = order
    p.match_status = status.UNDERPAID  # tạm: gắn vào đơn, xét đủ/thiếu theo tổng ngay dưới
    p.save(update_fields=["sales_order", "match_status"])

    if order_paid_total(order) >= order.total_amount:
        bank_amount = p.amount
        if p.amount >= order.total_amount:
            p.match_status = status.MATCHED  # một mình khoản này đủ đơn
            p.amount = order.total_amount  # L8: phần thừa (nếu có) tách dòng OVERPAID dưới
            p.save(update_fields=["match_status", "amount"])
            payments = [p]
        else:
            payments = list(_confirmable_payments(order).select_for_update())
        result = _issue_and_close(
            order, payments, clicked=p, clicked_resolution=PaymentTransaction.Resolution.ATTACHED,
            actor=actor, note=note,
        )
        if p.match_status == status.MATCHED:
            extra = split_overpaid(payment=p, order=order, bank_amount=bank_amount, actor=actor)
            if extra is not None:
                result["overpaid_amount"] = money_str(extra.amount)
        return result

    record_audit(
        "attach_payment", actor=actor, obj=p, note=note,
        changes={"order": order.code, "match_status": {"from": status.UNMATCHED, "to": p.match_status},
                 "paid_total": order_paid_total(order), "total_amount": order.total_amount},
    )
    return {
        "payment_id": p.pk, "resolution_status": p.resolution_status, "resolution": p.resolution,
        "order_status": order.status, "resolved_payment_ids": [],
    }


def _confirm_order(p, *, order, actor, note):
    if order is None:
        raise BusinessError(
            "Giao dịch chưa gắn đơn — gắn đơn trước (ATTACH_TO_ORDER).", code=RESOLVE_CODE
        )
    if order.status in (SalesOrder.Status.AUTO_CANCELLED, SalesOrder.Status.CANCELLED):
        _check_order_bookable(order)  # BR-TT-05
    if p.match_status != PaymentTransaction.MatchStatus.UNDERPAID:
        raise BusinessError("Chỉ xác nhận đơn từ giao dịch thiếu tiền.", code=RESOLVE_CODE)
    _check_order_bookable(order)

    payments = list(_confirmable_payments(order).select_for_update())
    if p.pk not in {x.pk for x in payments}:
        raise BusinessError(
            "Giao dịch đang có phiếu hoàn — không dùng để xác nhận đơn.", code=RESOLVE_CODE
        )
    received = order_paid_total(order)
    if received < order.total_amount:
        raise BusinessError(
            f"Tổng tiền đã nhận {vnd_short(received)} < tổng đơn {vnd_short(order.total_amount)}.",
            code=RESOLVE_CODE,
        )
    return _issue_and_close(
        order, payments, clicked=p, clicked_resolution=PaymentTransaction.Resolution.CONFIRMED,
        actor=actor, note=note,
    )


def _issue_and_close(order, payments, *, clicked, clicked_resolution, actor, note):
    """Đơn Giữ chỗ đã đủ tiền → hoá đơn (trừ kho theo lô đã giữ, BR-BH-06) + PROCESSING; đóng các giao dịch."""
    field_len = SalesInvoice._meta.get_field("payment_txn_ref").max_length
    txn_ref = ",".join(x.bank_txn_id for x in payments)[:field_len]
    now = timezone.now()
    old_status = order.status
    invoice = issue_invoice(order=order, txn_ref=txn_ref, issued_at=now)
    order.status = SalesOrder.Status.PROCESSING
    order.save(update_fields=["status"])

    for x in payments:
        x.resolution_status = PaymentTransaction.ResolutionStatus.RESOLVED
        x.resolution = (clicked_resolution if x.pk == clicked.pk
                        else PaymentTransaction.Resolution.CONFIRMED)
        x.resolved_by = actor
        x.resolved_at = now
        x.resolution_note = note
        x.save(update_fields=["resolution_status", "resolution", "resolved_by",
                              "resolved_at", "resolution_note"])
        record_audit(
            "resolve_payment", actor=actor, obj=x, note=note,
            changes={
                "resolution_status": {"from": PaymentTransaction.ResolutionStatus.OPEN,
                                      "to": x.resolution_status},
                "resolution": x.resolution,
                "order": order.code,
                "order_status": {"from": old_status, "to": order.status},
                "invoice": invoice.code,
                "via_payment": clicked.bank_txn_id,
            },
        )
    clicked.refresh_from_db()
    note_obj = invoice.delivery_notes.order_by("-id").first()
    return {
        "payment_id": clicked.pk,
        "resolution_status": clicked.resolution_status,
        "resolution": clicked.resolution,
        "order_status": order.status,
        "invoice_id": invoice.pk,
        "delivery_note_code": note_obj.code if note_obj else None,
        "resolved_payment_ids": [x.pk for x in payments],
    }


def mark_payment_refunded(*, payment, refund, actor):
    """
    S13-AC2 / BR-TT-09: phiếu hoàn gắn giao dịch được xác nhận → giao dịch RESOLVED/REFUNDED.
    Gọi trong transaction của `confirm_refund`. Giao dịch đã đóng → không đổi (idempotent).
    """
    p = PaymentTransaction.objects.select_for_update().get(pk=payment.pk)
    if p.resolution_status == PaymentTransaction.ResolutionStatus.RESOLVED:
        return p
    old = p.resolution_status
    p.resolution_status = PaymentTransaction.ResolutionStatus.RESOLVED
    p.resolution = PaymentTransaction.Resolution.REFUNDED
    p.resolved_by = actor
    p.resolved_at = refund.confirmed_at or timezone.now()
    p.resolution_note = f"Phiếu hoàn #{refund.pk} · mã GD hoàn {refund.bank_txn_ref}"
    p.save(update_fields=["resolution_status", "resolution", "resolved_by",
                          "resolved_at", "resolution_note"])
    record_audit(
        "resolve_payment", actor=actor, obj=p, note=p.resolution_note,
        changes={
            "resolution_status": {"from": old, "to": p.resolution_status},
            "resolution": p.resolution,
            "refund_id": refund.pk,
            "refund_amount": refund.amount,
            "bank_txn_ref": refund.bank_txn_ref,
        },
    )
    return p
