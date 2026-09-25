"""
Hoàn tiền (P-07): tạo phiếu hoàn (Chủ + Quản lý) và xác nhận đã hoàn (chỉ Chủ).
BR-HT-01/03/04/06/08. Thực thi tiền V1 là chuyển khoản tay — hệ thống chỉ ghi sổ.
"""
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from apps.common.audit import record_audit
from apps.common.exceptions import BusinessError
from apps.sales.models import Refund
from apps.sales.utils import ZERO
from apps.sales.utils import now as _now


# --- P-07: hoàn tiền ---------------------------------------------------------

def create_refund(*, invoice, amount, is_partial, reason, actor):
    """
    Tạo phiếu hoàn PENDING (BR-HT-01). BR-HT-04: số hoàn không vượt (đã thu − đã hoàn
    trước). Ghi AuditLog (BR-HT-08 / BR-PQ-05). Thực thi tiền là chuyển khoản tay (V1).
    """
    amount = Decimal(str(amount))
    if amount <= ZERO:
        raise BusinessError("Số tiền hoàn phải > 0.")

    with transaction.atomic():
        collected = invoice.amount  # đã thu = số tiền hoá đơn (BR-BC-01)
        prior = (
            invoice.refunds.exclude(status=Refund.Status.FAILED)
            .aggregate(total=Sum("amount"))
            .get("total")
            or ZERO
        )
        if amount > (collected - prior):
            raise BusinessError(
                "Số tiền hoàn vượt quá số đã thu trừ các lần hoàn trước (BR-HT-04)."
            )

        refund = Refund.objects.create(
            sales_invoice=invoice,
            amount=amount,
            is_partial=is_partial,
            method=Refund.Method.MANUAL_TRANSFER,
            status=Refund.Status.PENDING,
            reason=reason or "",
            created_by=actor,
        )
        record_audit(
            "create_refund", actor=actor, obj=refund,
            changes={"amount": {"to": amount}, "invoice": invoice.code},
        )
    return refund


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
        if r.status == Refund.Status.REFUNDED:
            raise BusinessError("Phiếu hoàn đã ở trạng thái Đã hoàn.")
        if r.status not in (Refund.Status.PENDING, Refund.Status.FAILED):
            raise BusinessError("Chỉ xác nhận hoàn cho phiếu đang chờ / thất bại.")

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
    return r
