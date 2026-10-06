"""
Xác định các bước tiếp theo (NextStep) và cung cấp Guidance cho Phiếu hoàn tiền (Refund).

Bất biến:
- Một nguồn cho cả guidance, available_actions và service check.
- Không rò PII (tên, SĐT, địa chỉ, nội dung CK).
- Không rò giá vốn.
- T1 view_refund giống hệt RefundViewSet.
"""
from apps.sales.refunds.scope import scope_refunds_for
from decimal import Decimal
from typing import Any, Optional

from django.conf import settings
from django.http import Http404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.common.guidance.api import register_guidance
from apps.common.guidance.reasons import get_reason
from apps.common.guidance.steps import Missing, NextStep, Why, step_to_dict
from apps.common.guidance.timeline import format_guidance_timeline
from apps.sales.models import Refund
from apps.sales.refunds.timeline import build_refund_timeline

ZERO = Decimal("0")


def check_confirm_refund(refund: Refund) -> list[Missing]:
    """Kiểm tra điều kiện nghiệp vụ để xác nhận hoàn tiền (BR-HT-03, BR-HT-08)."""
    missing: list[Missing] = []
    if refund.status != Refund.Status.PENDING:
        missing.append(Missing("BR-HT-08", get_reason("BR-HT-08")))
    return missing


def check_retry_refund(refund: Refund) -> list[Missing]:
    """Kiểm tra điều kiện nghiệp vụ để thử lại phiếu hoàn thất bại (BR-HT-04, BR-HT-08)."""
    from apps.sales.refunds.services import payment_refundable_amount, refundable_amount

    missing: list[Missing] = []
    if refund.status != Refund.Status.FAILED:
        missing.append(Missing("BR-HT-08", get_reason("BR-HT-08")))
        return missing

    if refund.sales_invoice_id:
        remaining = refundable_amount(invoice=refund.sales_invoice)
    elif refund.payment_transaction_id:
        remaining = payment_refundable_amount(payment=refund.payment_transaction)
    else:
        remaining = ZERO

    if refund.amount > remaining:
        missing.append(Missing("BR-HT-04", get_reason("BR-HT-04")))

    return missing


def get_refund_next_steps(refund: Refund, user: Any) -> list[NextStep]:
    """
    Trả danh sách NextStep cho phiếu hoàn dựa trên trạng thái và quyền của user.
    """
    steps: list[NextStep] = []

    if refund.status == Refund.Status.PENDING:
        can_confirm = user.has_perm("sales.confirm_refund")
        # Quản lý xem: allowed=false, missing có "Cần mã giao dịch chuyển khoản" (BR-HT-03, DW-04-AC1)
        missing_confirm = []
        if not can_confirm:
            missing_confirm.append(Missing("BR-HT-03", get_reason("BR-HT-03")))
            missing_confirm.append(Missing("BR-HT-07", get_reason("BR-HT-07")))

        steps.append(
            NextStep(
                key="confirm",
                label="Xác nhận đã hoàn",
                actor="user",
                allowed=can_confirm,
                who=["Chủ"],
                missing=missing_confirm,
                deadline=None,
                why=Why("BR-HT-03", get_reason("BR-HT-03")),
                command="sales.refund.confirm",
                ai=None,
            )
        )

        steps.append(
            NextStep(
                key="mark_failed",
                label="Báo thất bại",
                actor="user",
                allowed=can_confirm,
                who=["Chủ"],
                missing=[] if can_confirm else [Missing("BR-HT-07", get_reason("BR-HT-07"))],
                deadline=None,
                why=Why("BR-HT-08", get_reason("BR-HT-08")),
                command="sales.refund.mark_failed",
                ai=None,
            )
        )

    elif refund.status == Refund.Status.FAILED:
        can_confirm = user.has_perm("sales.confirm_refund")
        missing_biz = check_retry_refund(refund)
        missing_perm = [] if can_confirm else [Missing("BR-HT-07", get_reason("BR-HT-07"))]
        all_missing = missing_biz + missing_perm
        allowed = (len(missing_biz) == 0) and can_confirm

        steps.append(
            NextStep(
                key="retry",
                label="Thử lại hoàn tiền",
                actor="user",
                allowed=allowed,
                who=["Chủ"],
                missing=all_missing,
                deadline=None,
                why=Why("BR-HT-04", get_reason("BR-HT-04")),
                command="sales.refund.retry",
                ai=None,
            )
        )

    return steps


def get_refund_guidance(doc_id: str, user: Any, request: Optional[Any] = None) -> dict[str, Any]:
    """
    Guidance provider cho loại chứng từ "refund".
    """
    if not user.has_perm("sales.view_refund"):
        raise PermissionDenied("Bạn không có quyền xem phiếu hoàn tiền.")

    qs = Refund.objects.select_related(
        "sales_invoice__sales_order",
        "payment_transaction",
        "created_by__staff_profile",
        "confirmed_by__staff_profile",
    )

    qs = scope_refunds_for(user, qs)  # B1 (QA Lô 4+5): cùng phạm vi D1 với API phiếu hoàn; ngoài phạm vi là 404

    try:
        refund = qs.get(pk=int(doc_id))
    except (TypeError, ValueError, Refund.DoesNotExist):
        raise Http404("Không tìm thấy phiếu hoàn tiền.")

    doc_summary = {
        "type": "refund",
        "id": refund.pk,
        "code": refund.bank_txn_ref or f"REF-{refund.pk}",
        "status": refund.status,
        "status_label": refund.get_status_display(),
    }

    next_steps_objs = get_refund_next_steps(refund, user)
    next_steps_data = [step_to_dict(s, user=user) for s in next_steps_objs]

    timeline_events = build_refund_timeline(refund)
    timeline_data = format_guidance_timeline(timeline_events, viewer=user)

    warnings: list[dict[str, Any]] = []
    warning_days = getattr(settings, "GUIDANCE_REFUND_WARNING_DAYS", 25)
    if refund.status == Refund.Status.PENDING and refund.created_at:
        delta_days = (timezone.now() - refund.created_at).days
        if delta_days >= warning_days:
            warnings.append({
                "code": "GW-02",
                "text": "Phiếu hoàn gần hạn 30 ngày (BR-AI-33)",
            })

    related: list[dict[str, str]] = []
    if refund.sales_invoice:
        related.append({"type": "invoice", "code": refund.sales_invoice.code})
        if getattr(refund.sales_invoice, "sales_order", None):
            related.append({"type": "order", "code": refund.sales_invoice.sales_order.code})
    elif refund.payment_transaction:
        related.append({"type": "payment", "code": refund.payment_transaction.bank_txn_id})

    return {
        "doc": doc_summary,
        "next_steps": next_steps_data,
        "warnings": warnings,
        "timeline": timeline_data,
        "related": related,
    }


# Đăng ký tự động provider
register_guidance("refund", get_refund_guidance)
