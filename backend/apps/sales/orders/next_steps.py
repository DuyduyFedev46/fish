"""
Xác định các bước tiếp theo (NextStep) và cung cấp Guidance cho Đơn hàng (SalesOrder).

Bất biến:
- Một nguồn cho cả guidance, available_actions và service check.
- Không rò PII (tên, SĐT, địa chỉ, nội dung CK).
- Không rò giá vốn.
- T1 view_salesorder + T3 scope giống hệt SalesOrderViewSet.
"""
from decimal import Decimal
from typing import Any, Optional

from django.http import Http404
from rest_framework.exceptions import PermissionDenied

from apps.common.guidance.api import register_guidance
from apps.common.guidance.reasons import get_reason
from apps.common.guidance.steps import Missing, NextStep, Why, step_to_dict
from apps.common.guidance.timeline import format_guidance_timeline
from apps.delivery.models import DeliveryNote
from apps.sales.models import SalesOrder
from apps.sales.orders.timeline import build_timeline
from apps.sales.payments.services import MANUAL_CONFIRMABLE_STATUSES
from apps.sales.refunds.services import refundable_amount

ZERO = Decimal("0")


def check_cancel_order(order: SalesOrder) -> list[Missing]:
    """Kiểm tra điều kiện nghiệp vụ để huỷ đơn đã thanh toán (P-07, BR-GH-07)."""
    missing: list[Missing] = []
    if order.status not in (SalesOrder.Status.PAID, SalesOrder.Status.PROCESSING):
        missing.append(Missing("BR-GH-07", get_reason("BR-GH-07")))
        return missing

    invoice = getattr(order, "invoice", None)
    if invoice is None:
        missing.append(Missing("BR-GH-07", "Đơn chưa có hoá đơn"))
        return missing

    notes = list(invoice.delivery_notes.all())
    if notes and notes[0].status in (
        DeliveryNote.Status.DELIVERING,
        DeliveryNote.Status.COMPLETED,
        DeliveryNote.Status.CANCELLED,
    ):
        missing.append(Missing("BR-GH-07", get_reason("BR-GH-07")))

    return missing


def check_confirm_payment(order: SalesOrder) -> list[Missing]:
    """Kiểm tra điều kiện nghiệp vụ để xác nhận thanh toán tay (BR-TT-05, BR-TT-07)."""
    missing: list[Missing] = []
    if order.status not in MANUAL_CONFIRMABLE_STATUSES:
        missing.append(Missing("BR-TT-05", get_reason("BR-TT-05")))
    return missing


def get_order_next_steps(order: SalesOrder, user: Any) -> list[NextStep]:
    """
    Trả danh sách NextStep cho đơn hàng dựa trên trạng thái và quyền của user.
    """
    steps: list[NextStep] = []
    invoice = getattr(order, "invoice", None)

    # 1. Đơn BOOKED -> có bước hệ thống tự huỷ
    if order.status == SalesOrder.Status.BOOKED:
        deadline_str = order.booked_expires_at.isoformat() if order.booked_expires_at else None
        steps.append(
            NextStep(
                key="auto_cancel",
                label="Hệ thống sẽ tự huỷ",
                actor="system",
                allowed=False,
                who=["Hệ thống"],
                missing=[],
                deadline=deadline_str,
                why=Why("BR-BH-04", get_reason("BR-BH-04")),
                command=None,
                ai=None,
            )
        )

    # 2. Bước xác nhận thanh toán tay (confirm_payment)
    if order.status in MANUAL_CONFIRMABLE_STATUSES:
        missing_biz = check_confirm_payment(order)
        can_confirm = user.has_perm("sales.confirm_payment_manual")
        missing_perm = [] if can_confirm else [Missing("BR-TT-07", get_reason("BR-TT-07"))]
        all_missing = missing_biz + missing_perm
        allowed = (len(missing_biz) == 0) and can_confirm
        steps.append(
            NextStep(
                key="confirm_payment",
                label="Xác nhận thanh toán tay",
                actor="user",
                allowed=allowed,
                who=["Chủ"],
                missing=all_missing,
                deadline=None,
                why=Why("BR-TT-07", get_reason("BR-TT-07")),
                command="sales.salesorder.confirm_payment",
                ai=None,
            )
        )

    # 3. Bước huỷ đơn đã thanh toán (cancel)
    if order.status in (SalesOrder.Status.PAID, SalesOrder.Status.PROCESSING) and invoice is not None:
        missing_biz = check_cancel_order(order)
        can_cancel = user.has_perm("sales.cancel_paid_order")
        missing_perm = [] if can_cancel else [Missing("BR-PQ-12", get_reason("BR-PQ-12"))]
        all_missing = missing_biz + missing_perm
        allowed = (len(missing_biz) == 0) and can_cancel
        steps.append(
            NextStep(
                key="cancel",
                label="Huỷ đơn",
                actor="user",
                allowed=allowed,
                who=["Quản lý", "Chủ"],
                missing=all_missing,
                deadline=None,
                why=Why("BR-GH-07", get_reason("BR-GH-07")),
                command="sales.salesorder.cancel_order",
                ai=None,
            )
        )

    # 4. Bước tạo phiếu hoàn (create_refund)
    if invoice is not None and refundable_amount(invoice=invoice) > ZERO:
        can_refund = user.has_perm("sales.create_refund")
        missing = [] if can_refund else [Missing("BR-PQ-12", get_reason("BR-PQ-12"))]
        steps.append(
            NextStep(
                key="create_refund",
                label="Tạo phiếu hoàn",
                actor="user",
                allowed=can_refund,
                who=["Quản lý", "Chủ"],
                missing=missing,
                deadline=None,
                why=Why("BR-HT-04", get_reason("BR-HT-04")),
                command="sales.refund.create",
                ai=None,
            )
        )

    return steps


def get_order_guidance(doc_id: str, user: Any, request: Optional[Any] = None) -> dict[str, Any]:
    """
    Guidance provider cho loại chứng từ "order".
    """
    if not user.has_perm("sales.view_salesorder"):
        raise PermissionDenied("Bạn không có quyền xem đơn hàng.")

    qs = (
        SalesOrder.objects.all()
        .select_related("customer", "invoice")
        .prefetch_related(
            "payments",
            "lines",
            "invoice__delivery_notes",
            "invoice__refunds",
        )
    )

    # Phạm vi T3 (scope) như SalesOrderViewSet: NV giao chỉ thấy đơn của phiếu giao gán cho mình
    if user.groups.filter(name="nv_giao").exists() and not user.is_superuser:
        qs = qs.filter(invoice__delivery_notes__assigned_to=user).distinct()

    try:
        if str(doc_id).isdigit():
            order = qs.get(pk=int(doc_id))
        else:
            order = qs.get(code=doc_id)
    except SalesOrder.DoesNotExist:
        raise Http404(f"Không tìm thấy đơn hàng: {doc_id}")

    # doc: không bao gồm PII (tên, SĐT, địa chỉ khách)
    doc_summary = {
        "type": "order",
        "id": order.pk,
        "code": order.code,
        "status": order.status,
        "status_label": order.get_status_display(),
    }

    next_steps_objs = get_order_next_steps(order, user)
    next_steps_data = [step_to_dict(s) for s in next_steps_objs]

    timeline_events = build_timeline(order)
    timeline_data = format_guidance_timeline(timeline_events, viewer=user)

    related = []
    invoice = getattr(order, "invoice", None)
    if invoice is not None:
        related.append({"type": "invoice", "code": invoice.code})
        for n in sorted(invoice.delivery_notes.all(), key=lambda n: n.pk):
            related.append({"type": "delivery", "code": n.code})
        for r in sorted(invoice.refunds.all(), key=lambda r: r.pk):
            ref_code = r.bank_txn_ref or f"REF-{r.pk}"
            related.append({"type": "refund", "code": ref_code})

    warnings: list[dict[str, Any]] = []

    return {
        "doc": doc_summary,
        "next_steps": next_steps_data,
        "warnings": warnings,
        "timeline": timeline_data,
        "related": related,
    }


# Tự động đăng ký provider
register_guidance("order", get_order_guidance)
