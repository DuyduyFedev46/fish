"""
Tự động xác nhận thanh toán cho ca khớp tuyệt đối (DW-26, V-DW1, 01-analysis §7.3).
Job Hệ thống (actor_kind=system), công tắc riêng system.auto_confirm_exact_match của Chủ,
gọi đúng service ghi tiền hiện có, không đưa raw_payload/nội dung CK vào model hay log.
"""
import logging
import re
from decimal import Decimal
from django.conf import settings
from django.db import transaction

from apps.ai.models import AiAction, AiPolicyVersion
from apps.common.audit import record_audit
from apps.sales.models import PaymentTransaction, SalesOrder
from apps.sales.payments import services as payment_services

logger = logging.getLogger(__name__)


def process_exact_payment_matches() -> dict:
    """
    Quét các giao dịch mở trong hàng chờ lệch và tự động khớp các ca đạt chuẩn khớp tuyệt đối (DW-26).
    Trả về dict thống kê kết quả: {"confirmed": int, "escalated": int, "skipped": int, "reason": str|None}.
    """
    # 1. Kiểm tra môi trường production (DW-26-AC5)
    if not getattr(settings, "AI_PRODUCTION_READY", False):
        logger.info("DW-26: Production mode disabled auto-confirm (BR-AI-27)")
        return {"confirmed": 0, "escalated": 0, "skipped": 0, "reason": "PRODUCTION_NOT_READY"}

    # 2. Kiểm tra cờ AI_ENABLED (DW-26-AC6)
    if not getattr(settings, "AI_ENABLED", False):
        logger.info("DW-26: AI is disabled")
        return {"confirmed": 0, "escalated": 0, "skipped": 0, "reason": "AI_DISABLED"}

    # 3. Kiểm tra công tắc riêng của Chủ (V-DW1)
    latest_policy = AiPolicyVersion.objects.order_by("-version").first()
    red_zone_open = latest_policy.red_zone_open if latest_policy else {}
    if not red_zone_open.get("system.auto_confirm_exact_match", False):
        logger.info("DW-26: Switch system.auto_confirm_exact_match is closed by owner")
        return {"confirmed": 0, "escalated": 0, "skipped": 0, "reason": "SWITCH_CLOSED"}

    # 4. Quét các giao dịch lệch đang mở (OPEN)
    open_txns = list(
        PaymentTransaction.objects.filter(
            resolution_status=PaymentTransaction.ResolutionStatus.OPEN
        ).order_by("received_at", "id")
    )

    confirmed_count = 0
    escalated_count = 0
    skipped_count = 0

    for txn_item in open_txns:
        with transaction.atomic():
            p = (
                PaymentTransaction.objects.select_for_update(skip_locked=True)
                .filter(pk=txn_item.pk, resolution_status=PaymentTransaction.ResolutionStatus.OPEN)
                .first()
            )
            if p is None:
                skipped_count += 1
                continue

            # a. Kiểm tra cờ nghi trùng (BR-TT-15)
            if p.duplicate_warning:
                _escalate_to_chu(p, reason="Giao dịch có cảnh báo nghi trùng xác nhận tay (BR-TT-15)")
                escalated_count += 1
                continue

            # b. Kiểm tra môi trường cổng (BR-TT-14)
            if p.environment:
                current_env = (getattr(settings, "SEPAY_ENV", "") or "").strip().upper()
                if p.environment != current_env:
                    _escalate_to_chu(
                        p,
                        reason=f"Sai môi trường cổng: giao dịch {p.environment} khác hệ thống {current_env} (BR-TT-14)",
                    )
                    escalated_count += 1
                    continue

            # c. Xác định đơn hàng ứng viên
            candidate_orders = []
            if p.sales_order is not None:
                candidate_orders = [p.sales_order]
            else:
                raw = p.raw_payload if isinstance(p.raw_payload, dict) else {}
                order_code = str(raw.get("order_code") or "").strip()
                if not order_code:
                    desc = f"{raw.get('description', '')} {raw.get('content', '')}"
                    m = re.search(r"\b(SO-\d{6}-[A-Za-z0-9]+)\b", desc)
                    if m:
                        order_code = m.group(1)

                if order_code:
                    candidate_orders = list(SalesOrder.objects.filter(code=order_code))

            # d. Kiểm tra số lượng đơn khớp
            if len(candidate_orders) == 0:
                _escalate_to_chu(p, reason="Không tìm thấy đơn hàng khớp với giao dịch")
                escalated_count += 1
                continue
            elif len(candidate_orders) > 1:
                _escalate_to_chu(p, reason="Giao dịch khớp với nhiều hơn 1 đơn hàng")
                escalated_count += 1
                continue

            order = candidate_orders[0]

            # e. Kiểm tra trạng thái đơn hàng (chỉ nhận BOOKED)
            if order.status != SalesOrder.Status.BOOKED:
                _escalate_to_chu(
                    p,
                    reason=f"Đơn {order.code} ở trạng thái {order.get_status_display()}, không thể tự xác nhận (BR-TT-05)",
                )
                escalated_count += 1
                continue

            # f. Kiểm tra số tiền (khớp chính xác 100%)
            if p.amount != order.total_amount:
                diff = p.amount - order.total_amount
                status_text = "Thiếu tiền" if diff < Decimal("0") else "Thừa tiền"
                _escalate_to_chu(
                    p,
                    reason=f"{status_text}: Giao dịch {p.amount}đ khác tổng đơn {order.total_amount}đ (BR-TT-04/10)",
                )
                escalated_count += 1
                continue

            # g. ĐẠT CHUẨN KHỚP TUYỆT ĐỐI -> GỌI SERVICE GHI TIỀN HIỆN CÓ
            try:
                if p.sales_order is None:
                    payment_services.resolve_payment(
                        payment=p,
                        action=payment_services.ResolveAction.ATTACH_TO_ORDER,
                        order_id=order.id,
                        actor=None,
                        note="Hệ thống tự động khớp tuyệt đối (DW-26)",
                    )
                else:
                    payment_services.resolve_payment(
                        payment=p,
                        action=payment_services.ResolveAction.CONFIRM_ORDER,
                        actor=None,
                        note="Hệ thống tự động khớp tuyệt đối (DW-26)",
                    )

                record_audit(
                    "auto_confirm_exact_match",
                    actor=None,
                    actor_kind="system",
                    obj=p,
                    note=f"Hệ thống tự động xác nhận giao dịch {p.bank_txn_id} cho đơn {order.code}",
                )

                # DW-26-AC3: Log chỉ in mã GD + mã đơn, không in nội dung CK hay PII
                logger.info(f"Auto-confirmed exact match: txn {p.bank_txn_id} -> order {order.code}")
                confirmed_count += 1
            except Exception as exc:
                logger.warning(f"Error auto-confirming txn {p.bank_txn_id} -> order {order.code}: {exc}")
                _escalate_to_chu(p, reason=f"Lỗi khi xử lý xác nhận thanh toán: {exc}")
                escalated_count += 1

    return {"confirmed": confirmed_count, "escalated": escalated_count, "skipped": skipped_count}


def _escalate_to_chu(payment: PaymentTransaction, *, reason: str):
    """Tạo hoặc cập nhật AiAction ESCALATED chuyển việc cho Chủ (DW-26-AC2)."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    chu_user = User.objects.filter(groups__name="chu", is_active=True).first() or User.objects.filter(is_active=True).first()

    action, created = AiAction.objects.get_or_create(
        target_model="paymenttransaction",
        target_id=str(payment.id),
        command="sales.paymenttransaction.resolve",
        defaults={
            "kind": AiAction.Kind.WRITE,
            "level": AiAction.Level.C,
            "status": AiAction.Status.ESCALATED,
            "assignee_group": "chu",
            "owner": chu_user,
            "downgrade_reason": {"code": "AI_MISMATCH", "text": reason},
            "args": {"payment_id": payment.id, "reason": reason},
        },
    )
    if not created and action.status != AiAction.Status.ESCALATED:
        action.status = AiAction.Status.ESCALATED
        action.assignee_group = "chu"
        action.downgrade_reason = {"code": "AI_MISMATCH", "text": reason}
        action.save(update_fields=["status", "assignee_group", "downgrade_reason"])

    record_audit(
        "escalate_unmatched_payment",
        actor=None,
        actor_kind="system",
        obj=payment,
        note=f"Chuyển Chủ xử lý giao dịch lệch {payment.bank_txn_id}: {reason}",
    )
    # DW-26-AC3: Log chỉ in mã GD và lý do, không in PII hay nội dung CK
    logger.info(f"Escalated unmatched txn {payment.bank_txn_id} to chu: {reason}")
