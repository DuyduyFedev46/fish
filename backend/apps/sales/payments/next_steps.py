"""
Xác định các bước tiếp theo (NextStep) và cung cấp Guidance cho Giao dịch thanh toán (PaymentTransaction).

Bất biến:
- Một nguồn cho cả guidance, available_actions và service check.
- Không rò PII (tuyệt đối không raw_payload, nội dung CK, tên người chuyển - DW-04-AC4).
- Không rò giá vốn.
- T1 view_paymenttransaction + RESOLVE_PERM giống hệt PaymentTransactionViewSet (DW-04-AC5).
"""
from decimal import Decimal
from typing import Any, Optional

from django.http import Http404
from rest_framework.exceptions import PermissionDenied

from apps.common.guidance.api import register_guidance
from apps.common.guidance.reasons import get_reason
from apps.common.guidance.steps import Missing, NextStep, Why, step_to_dict
from apps.common.guidance.timeline import format_guidance_timeline
from apps.sales.models import PaymentTransaction, SalesOrder
from apps.sales.payments.timeline import build_payment_timeline

ZERO = Decimal("0")


def get_payment_next_steps(payment: PaymentTransaction, user: Any) -> list[NextStep]:
    """
    Trả danh sách NextStep cho giao dịch thanh toán trong hàng chờ lệch.
    """
    from apps.sales.payments.services import (
        RESOLVE_PERM,
        _confirmable_payments,
        order_paid_total,
    )
    from apps.sales.refunds.services import payment_refundable_amount

    steps: list[NextStep] = []

    if payment.resolution_status != PaymentTransaction.ResolutionStatus.OPEN:
        return steps

    can_resolve = user.has_perm(RESOLVE_PERM)
    status_match = PaymentTransaction.MatchStatus
    order = payment.sales_order

    # 1. Gắn vào đơn hàng (attach_to_order) khi UNMATCHED và chưa có đơn
    if payment.match_status == status_match.UNMATCHED and order is None:
        missing_perm = [] if can_resolve else [Missing("BR-TT-07", get_reason("BR-TT-07"))]
        steps.append(
            NextStep(
                key="attach_to_order",
                label="Gắn vào đơn hàng",
                actor="user",
                allowed=can_resolve,
                who=["Chủ"],
                missing=missing_perm,
                deadline=None,
                why=Why("BR-TT-09", get_reason("BR-TT-09")),
                command="sales.paymenttransaction.resolve",
                ai=None,
            )
        )

    # 2. Xác nhận đơn khi đã bù đủ (confirm_order) khi UNDERPAID và có đơn
    if payment.match_status == status_match.UNDERPAID and order is not None:
        is_booked = (order.status == SalesOrder.Status.BOOKED)
        is_in_confirmable = _confirmable_payments(order).filter(pk=payment.pk).exists()
        is_paid_enough = (order_paid_total(order) >= order.total_amount)

        missing: list[Missing] = []
        if not is_paid_enough:
            missing.append(Missing("BR-TT-04", get_reason("BR-TT-04")))
        if not can_resolve:
            missing.append(Missing("BR-TT-07", get_reason("BR-TT-07")))

        allowed = is_booked and is_in_confirmable and is_paid_enough and can_resolve
        steps.append(
            NextStep(
                key="confirm_order",
                label="Xác nhận đơn khi đã bù đủ",
                actor="user",
                allowed=allowed,
                who=["Chủ"],
                missing=missing,
                deadline=None,
                why=Why("BR-TT-04", get_reason("BR-TT-04")),
                command="sales.paymenttransaction.resolve",
                ai=None,
            )
        )

    # 3. Tạo phiếu hoàn tiền (refund)
    rem_amount = payment_refundable_amount(payment=payment)
    if rem_amount > ZERO:
        can_refund = user.has_perm("sales.create_refund") and can_resolve
        missing_perm = [] if can_refund else [Missing("BR-PQ-12", get_reason("BR-PQ-12"))]
        steps.append(
            NextStep(
                key="refund",
                label="Tạo phiếu hoàn",
                actor="user",
                allowed=can_refund,
                who=["Chủ"],
                missing=missing_perm,
                deadline=None,
                why=Why("BR-TT-10", get_reason("BR-TT-10")),
                command="sales.refund.create_refund",
                ai=None,
            )
        )

    return steps


def get_payment_guidance(doc_id: str, user: Any, request: Optional[Any] = None) -> dict[str, Any]:
    """
    Guidance provider cho loại chứng từ "payment".
    """
    from apps.sales.payments.services import RESOLVE_PERM

    # Cùng mã lỗi 403 với PaymentTransactionViewSet (DW-04-AC5)
    if not (user.has_perm("sales.view_paymenttransaction") and user.has_perm(RESOLVE_PERM)):
        raise PermissionDenied("Bạn không có quyền xem giao dịch thanh toán.")

    qs = PaymentTransaction.objects.select_related(
        "sales_order",
        "resolved_by__staff_profile",
    ).prefetch_related("refunds")

    try:
        payment = qs.get(pk=int(doc_id))
    except (TypeError, ValueError, PaymentTransaction.DoesNotExist):
        raise Http404("Không tìm thấy giao dịch thanh toán.")

    # doc: TUYỆT ĐỐI không đưa raw_payload, description, counter_account_name (DW-04-AC4)
    doc_summary = {
        "type": "payment",
        "id": payment.pk,
        "code": payment.bank_txn_id,
        "status": payment.resolution_status,
        "status_label": payment.get_resolution_status_display(),
    }

    next_steps_objs = get_payment_next_steps(payment, user)
    next_steps_data = [step_to_dict(s, user=user) for s in next_steps_objs]

    timeline_events = build_payment_timeline(payment)
    timeline_data = format_guidance_timeline(timeline_events, viewer=user)

    warnings: list[dict[str, Any]] = []
    if payment.duplicate_warning:  # BR-TT-15 / BR-TT-18: nhãn nằm ở `duplicate_warning`, áp cho mọi loại khoản
        warnings.append({
            "code": "GW-03",
            "text": payment.duplicate_warning,
        })

    related: list[dict[str, str]] = []
    if payment.sales_order:
        related.append({"type": "order", "code": payment.sales_order.code})
    for r in sorted(payment.refunds.all(), key=lambda r: r.pk):
        ref_code = r.bank_txn_ref or f"REF-{r.pk}"
        related.append({"type": "refund", "code": ref_code})

    return {
        "doc": doc_summary,
        "next_steps": next_steps_data,
        "warnings": warnings,
        "timeline": timeline_data,
        "related": related,
    }


# Đăng ký tự động provider
register_guidance("payment", get_payment_guidance)
