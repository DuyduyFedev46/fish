"""
Hoàn tiền (P-07): tạo phiếu hoàn (Chủ + Quản lý) và xác nhận đã hoàn (chỉ Chủ).
BR-HT-01/03/04/06/08. Thực thi tiền V1 là chuyển khoản tay — hệ thống chỉ ghi sổ.

S13 (Q9): phiếu hoàn gắn thẳng GIAO DỊCH THANH TOÁN khi không có hoá đơn (tiền về sau khi
huỷ, thiếu mà khách không bù, chuyển thừa) — `create_refund_for_payment`; xác nhận phiếu đó
→ giao dịch RESOLVED/REFUNDED (BR-TT-09). Khoản này chưa từng ghi doanh thu nên báo cáo kỳ
không trừ (BR-BC-03/BR-TT-06). `request_id` (Q12) chống tạo trùng khi bấm đúp.
"""
import uuid

from django.db import transaction
from django.db.models import Sum

from apps.common.audit import record_audit
from apps.common.exceptions import BusinessError
from apps.sales.models import PaymentTransaction, Refund
from apps.sales.utils import ZERO, vnd_short
from apps.sales.utils import now as _now


# --- P-07: hoàn tiền ---------------------------------------------------------

def refundable_amount(*, invoice):
    """BR-HT-04: còn hoàn được = đã thu (số tiền hoá đơn, BR-BC-01) − các phiếu hoàn chưa thất bại."""
    prior = (
        invoice.refunds.exclude(status=Refund.Status.FAILED)
        .aggregate(total=Sum("amount"))
        .get("total")
        or ZERO
    )
    return invoice.amount - prior


REFUND_AMOUNT_CODE = "BR-HT-04"
REFUND_SOURCE_CODE = "BR-HT-01"
REFUND_STATUS_CODE = "BR-HT-09"  # S16: phiếu hoàn sai trạng thái để đổi (confirm/mark-failed/retry)
REFUND_AMOUNT_INVALID_MSG = "Số tiền hoàn phải lớn hơn 0."
REFUND_AMOUNT_MIN_MSG = "Số tiền hoàn tối thiểu 1đ."
REFUND_ALREADY_REFUNDED_MSG = "Phiếu đã hoàn, không đổi trạng thái được."


def parse_refund_amount(raw):
    """BR-HT-04: số tiền hoàn ≥ 1đ, hữu hạn, trong miền cột (dùng chung kiểm tiền của thanh toán)."""
    from apps.sales.payments.services import AMOUNT_INVALID_MSG, AMOUNT_MIN_MSG, validate_amount

    try:
        return validate_amount(raw)
    except ValueError as exc:
        msg = {AMOUNT_INVALID_MSG: REFUND_AMOUNT_INVALID_MSG,
               AMOUNT_MIN_MSG: REFUND_AMOUNT_MIN_MSG}.get(str(exc), str(exc))
        raise BusinessError(msg, code=REFUND_AMOUNT_CODE) from None


def parse_request_id(raw):
    """Q12: `request_id` là UUID do FE sinh; bỏ trống → None (không chống trùng)."""
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return None
    try:
        return uuid.UUID(str(raw).strip())
    except (TypeError, ValueError, AttributeError):
        raise BusinessError("request_id phải là UUID.", code=REFUND_SOURCE_CODE) from None


def find_duplicate(*, request_id, invoice=None, payment=None):
    """
    Q12: đã có phiếu cùng `request_id` → trả phiếu đó (bấm đúp / mạng chậm gửi lại).
    Cùng `request_id` nhưng khác chứng từ gốc → lỗi (không trả phiếu của chứng từ khác).
    """
    if request_id is None:
        return None
    existing = Refund.objects.filter(request_id=request_id).first()
    if existing is None:
        return None
    same = (
        (invoice is not None and existing.sales_invoice_id == invoice.pk)
        or (payment is not None and existing.payment_transaction_id == payment.pk)
    )
    if not same:
        raise BusinessError("request_id đã dùng cho phiếu hoàn khác.", code=REFUND_SOURCE_CODE)
    return existing


def payment_refundable_amount(*, payment):
    """BR-HT-04 (S13): còn hoàn được = số tiền giao dịch − các phiếu hoàn chưa thất bại gắn giao dịch."""
    prior = (
        payment.refunds.exclude(status=Refund.Status.FAILED)
        .aggregate(total=Sum("amount"))
        .get("total")
        or ZERO
    )
    return max(payment.amount - prior, ZERO)


def create_refund_for_payment(*, payment, amount, reason, actor, is_partial=None, request_id=None):
    """
    S13: phiếu hoàn PENDING gắn giao dịch lệch KHÔNG có hoá đơn (BR-HT-01, Q9).
    Chỉ giao dịch còn trong hàng chờ (OPEN). Khoá dòng giao dịch rồi mới kiểm số còn hoàn
    → hai lần bấm đồng thời không vượt BR-HT-04. Trả `(refund, duplicate)`.
    """
    amount = parse_refund_amount(amount)
    with transaction.atomic():
        p = PaymentTransaction.objects.select_for_update().get(pk=payment.pk)
        dup = find_duplicate(request_id=request_id, payment=p)
        if dup is not None:
            return dup, True
        if p.resolution_status == PaymentTransaction.ResolutionStatus.RESOLVED:
            raise BusinessError("Giao dịch đã được xử lý, không lập phiếu hoàn.", code="BR-TT-09")
        if p.resolution_status != PaymentTransaction.ResolutionStatus.OPEN:
            raise BusinessError(
                "Giao dịch đã khớp hoá đơn — lập phiếu hoàn từ hoá đơn.", code=REFUND_SOURCE_CODE
            )
        remaining = payment_refundable_amount(payment=p)
        if amount > remaining:
            raise BusinessError(
                f"Vượt số tiền còn được hoàn: tối đa {vnd_short(remaining)}.",
                code=REFUND_AMOUNT_CODE,
            )
        refund = Refund.objects.create(
            payment_transaction=p,
            amount=amount,
            is_partial=(amount < p.amount) if is_partial is None else bool(is_partial),
            method=Refund.Method.MANUAL_TRANSFER,
            status=Refund.Status.PENDING,
            reason=reason or "",
            created_by=actor,
            request_id=request_id,
        )
        record_audit(
            "create_refund", actor=actor, obj=refund,
            changes={"amount": {"to": amount}, "payment_transaction": p.bank_txn_id,
                     "match_status": p.match_status},
        )
    return refund, False


def create_refund(*, invoice, amount, is_partial, reason, actor, request_id=None):
    """
    Tạo phiếu hoàn PENDING (BR-HT-01). BR-HT-04: số hoàn không vượt (đã thu − đã hoàn
    trước). Ghi AuditLog (BR-HT-08 / BR-PQ-05). Thực thi tiền là chuyển khoản tay (V1).
    """
    refund, _duplicate = create_invoice_refund(
        invoice=invoice, amount=amount, is_partial=is_partial, reason=reason, actor=actor,
        request_id=request_id,
    )
    return refund


def create_invoice_refund(*, invoice, amount, is_partial, reason, actor, request_id=None):
    """
    Như `create_refund` nhưng trả `(refund, duplicate)` cho API. Khoá dòng hoá đơn trước khi
    kiểm trùng `request_id` và số còn hoàn → hai lần bấm đồng thời xếp hàng (Q12, BR-HT-04).
    """
    from apps.sales.models import SalesInvoice

    amount = parse_refund_amount(amount)  # BR-HT-04: ≥ 1đ, cả khi gọi thẳng service

    with transaction.atomic():
        invoice = SalesInvoice.objects.select_for_update().get(pk=invoice.pk)
        dup = find_duplicate(request_id=request_id, invoice=invoice)
        if dup is not None:
            return dup, True
        remaining = refundable_amount(invoice=invoice)
        if amount > remaining:
            raise BusinessError(
                f"Vượt số đã thu: còn được hoàn tối đa {vnd_short(remaining)}.",
                code=REFUND_AMOUNT_CODE,
            )

        refund = Refund.objects.create(
            sales_invoice=invoice,
            amount=amount,
            is_partial=is_partial,
            method=Refund.Method.MANUAL_TRANSFER,
            status=Refund.Status.PENDING,
            reason=reason or "",
            created_by=actor,
            request_id=request_id,
        )
        record_audit(
            "create_refund", actor=actor, obj=refund,
            changes={"amount": {"to": amount}, "invoice": invoice.code},
        )
    return refund, False


def _block_if_already_refunded(r):
    """BR-HT-09: phiếu Đã hoàn là điểm không quay lui — confirm/mark-failed/retry đều chặn."""
    if r.status == Refund.Status.REFUNDED:
        raise BusinessError(REFUND_ALREADY_REFUNDED_MSG, code=REFUND_STATUS_CODE)


def confirm_refund(*, refund, bank_txn_ref, actor):
    """
    Xác nhận đã hoàn (PENDING -> REFUNDED). BẮT BUỘC bank_txn_ref (BR-HT-03) — không cho
    xác nhận suông. Phiếu REFUNDED (ở kỳ confirmed_at) chính là bút toán ĐẢO doanh thu,
    ghi vào kỳ phát sinh hoàn, không sửa kỳ cũ (BR-HT-06). Ghi AuditLog (BR-HT-08).
    """
    if not bank_txn_ref:
        raise BusinessError("Xác nhận hoàn bắt buộc nhập mã giao dịch chuyển khoản (BR-HT-03).")

    with transaction.atomic():
        r = Refund.objects.select_for_update().get(pk=refund.pk)
        _block_if_already_refunded(r)
        if r.status not in (Refund.Status.PENDING, Refund.Status.FAILED):
            raise BusinessError(
                "Chỉ xác nhận hoàn cho phiếu đang chờ / thất bại.", code=REFUND_STATUS_CODE,
            )

        old_status = r.status
        r.status = Refund.Status.REFUNDED
        r.bank_txn_ref = bank_txn_ref
        r.confirmed_by = actor
        r.confirmed_at = _now()
        r.save(update_fields=["status", "bank_txn_ref", "confirmed_by", "confirmed_at"])
        record_audit(
            "confirm_refund", actor=actor, obj=r,
            changes={
                "status": {"from": old_status, "to": r.status},
                "bank_txn_ref": bank_txn_ref,
            },
        )
        if r.payment_transaction_id is not None:  # S13-AC2 / BR-TT-09
            from apps.sales.payments.services import mark_payment_refunded

            mark_payment_refunded(payment=r.payment_transaction, refund=r, actor=actor)
    return r


# --- S16: phiếu hoàn chờ chuyển — báo thất bại / thử lại (BR-HT-09) ----------

def mark_refund_failed(*, refund, reason, actor):
    """
    PENDING -> FAILED: Chủ báo chuyển khoản thất bại (vd sai số tài khoản). Giải phóng lại
    số tiền của phiếu này cho lần hoàn khác (BR-HT-04: `refundable_amount`/
    `payment_refundable_amount` loại phiếu FAILED khỏi tổng đã hoàn). Ghi AuditLog.
    """
    with transaction.atomic():
        r = Refund.objects.select_for_update().get(pk=refund.pk)
        _block_if_already_refunded(r)
        if r.status != Refund.Status.PENDING:
            raise BusinessError(
                "Chỉ báo thất bại được khi phiếu đang Chờ hoàn.", code=REFUND_STATUS_CODE,
            )
        old_status = r.status
        r.status = Refund.Status.FAILED
        r.failure_reason = reason or ""
        r.save(update_fields=["status", "failure_reason"])
        record_audit(
            "mark_refund_failed", actor=actor, obj=r,
            changes={"status": {"from": old_status, "to": r.status}},
            note=reason or "",
        )
    return r


def retry_refund(*, refund, actor):
    """
    FAILED -> PENDING: Chủ thử chuyển lại. Vì phiếu FAILED không tính vào tổng đã hoàn
    (BR-HT-04), lúc thử lại phải kiểm lại số còn hoàn — trong lúc chờ, một phiếu khác có
    thể đã lấp đầy phần còn trống (S16-AC6). Ghi AuditLog.
    """
    with transaction.atomic():
        r = Refund.objects.select_for_update().get(pk=refund.pk)
        _block_if_already_refunded(r)
        if r.status != Refund.Status.FAILED:
            raise BusinessError(
                "Chỉ thử lại được khi phiếu đang Thất bại.", code=REFUND_STATUS_CODE,
            )
        if r.sales_invoice_id:
            remaining = refundable_amount(invoice=r.sales_invoice)
        else:
            remaining = payment_refundable_amount(payment=r.payment_transaction)
        if r.amount > remaining:
            raise BusinessError(
                f"Vượt số tiền còn được hoàn: tối đa {vnd_short(remaining)}.",
                code=REFUND_AMOUNT_CODE,
            )
        old_status = r.status
        r.status = Refund.Status.PENDING
        r.failure_reason = ""
        r.save(update_fields=["status", "failure_reason"])
        record_audit(
            "retry_refund", actor=actor, obj=r,
            changes={"status": {"from": old_status, "to": r.status}},
        )
    return r


def refund_available_actions(*, refund, user):
    """
    Thao tác trên một phiếu hoàn ở hàng chờ (`available_actions`): confirm/mark_failed khi
    Chờ hoàn; retry khi Thất bại. Mọi thao tác đòi `confirm_refund` (chỉ Chủ — BR-HT-07,
    ranh giới "tiền rời túi").
    """
    if not user.has_perm("sales.confirm_refund"):
        return []
    if refund.status == Refund.Status.PENDING:
        return ["confirm", "mark_failed"]
    if refund.status == Refund.Status.FAILED:
        return ["retry"]
    return []
