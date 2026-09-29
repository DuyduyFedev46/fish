"""
Các luật an toàn và điều kiện sàn nghiệp vụ cho AI Digital Worker (01-analysis §7.1, 02b §4.2, DW-25).
"""
import datetime
from django.db import models
from django.utils import timezone

from apps.inventory.batches.services import check_close_batch, ZERO
from apps.inventory.models import (
    Batch,
    ReturnToStock,
    StockLedgerEntry,
    StockReconciliation,
    StockReconciliationLine,
)
from apps.purchasing.models import PurchaseCostAllocation
from apps.sales.models import PaymentTransaction, Refund, SalesOrderLineBatch


def check_ai_close_batch_conditions(batch: Batch, *, current_action_id=None) -> tuple[bool, dict | None]:
    """
    Kiểm tra điều kiện sàn cho AI chốt lô trì hoãn (DW-25, Q-M6, BR-LO-04, BR-KK-05):
    1. Đủ điều kiện check_close_batch (tồn = 0 hoặc EXPIRED/CANCELLED, đã có hoá đơn mua, không còn đơn mở...).
    2. Ít nhất 7 ngày không có chi phí mua hàng mới phát sinh (Q-M6).
    3. Biên bản kiểm kê kho đã duyệt phải diễn ra sau lần xuất kho cuối cùng của lô (Q-M6).
    4. Không có phiếu hoàn (SalesRefund), hàng hoàn (CustomerReturn / ReturnToStock), hoặc giao dịch chưa khớp (PaymentTransaction) đang chờ xử lý tham chiếu lô.
    5. Không có AiAction PENDING hoặc SCHEDULED khác trên lô này.

    Trả về: (True, None) nếu đủ điều kiện;
            (False, {"code": "AI_CLOSE_BATCH_CONDITIONS_NOT_MET", "text": "..."}) nếu thiếu điều kiện.
    """
    if batch is None:
        return False, {
            "code": "AI_CLOSE_BATCH_CONDITIONS_NOT_MET",
            "text": "Lô cá không tồn tại.",
        }

    # 1. Kiểm tra check_close_batch
    missing = check_close_batch(batch)
    if missing:
        return False, {
            "code": "AI_CLOSE_BATCH_CONDITIONS_NOT_MET",
            "text": f"Lô chưa đủ điều kiện sàn chốt lô: {missing[0].text}",
        }

    now = timezone.now()

    # 2. Q-M6: 7 ngày không có chi phí mới
    recent_costs = PurchaseCostAllocation.objects.filter(
        batch=batch,
        purchase_cost__created_at__gte=now - datetime.timedelta(days=7),
    )
    if recent_costs.exists():
        return False, {
            "code": "AI_CLOSE_BATCH_CONDITIONS_NOT_MET",
            "text": "Lô có chi phí mua hàng mới phát sinh trong vòng 7 ngày qua.",
        }

    # 3. Q-M6: Kiểm kê đã duyệt sau lần xuất cuối
    last_out_movement = (
        StockLedgerEntry.objects.filter(batch=batch, qty_change__lt=ZERO)
        .order_by("-created_at")
        .first()
    )

    approved_recon_lines = StockReconciliationLine.objects.filter(
        batch=batch,
        reconciliation__status=StockReconciliation.Status.APPROVED,
    ).select_related("reconciliation")

    if not approved_recon_lines.exists():
        return False, {
            "code": "AI_CLOSE_BATCH_CONDITIONS_NOT_MET",
            "text": "Lô chưa có biên bản kiểm kê kho đã được duyệt.",
        }

    if last_out_movement:
        # Tìm thời điểm kiểm kê đã duyệt gần nhất
        latest_recon_time = None
        for r_line in approved_recon_lines:
            r_time = r_line.reconciliation.approved_at or r_line.reconciliation.created_at
            if latest_recon_time is None or r_time > latest_recon_time:
                latest_recon_time = r_time

        if latest_recon_time and latest_recon_time < last_out_movement.created_at:
            return False, {
                "code": "AI_CLOSE_BATCH_CONDITIONS_NOT_MET",
                "text": "Biên bản kiểm kê đã duyệt diễn ra trước lần xuất kho cuối cùng của lô.",
            }

    # 4. Không có phiếu hoàn, hàng hoàn, giao dịch lệch chờ
    order_ids = list(
        SalesOrderLineBatch.objects.filter(batch=batch)
        .values_list("order_line__order_id", flat=True)
        .distinct()
    )

    if order_ids:
        # Phiếu hoàn tiền chờ duyệt
        pending_refunds = Refund.objects.filter(
            models.Q(sales_invoice__sales_order_id__in=order_ids)
            | models.Q(payment_transaction__order_id__in=order_ids),
            status=Refund.Status.PENDING,
        )
        if pending_refunds.exists():
            return False, {
                "code": "AI_CLOSE_BATCH_CONDITIONS_NOT_MET",
                "text": "Còn phiếu hoàn tiền đang chờ xử lý liên quan tới đơn hàng của lô.",
            }

        # Giao dịch thanh toán chưa khớp
        open_txns = PaymentTransaction.objects.filter(
            order_id__in=order_ids,
            resolution_status=PaymentTransaction.ResolutionStatus.OPEN,
        )
        if open_txns.exists():
            return False, {
                "code": "AI_CLOSE_BATCH_CONDITIONS_NOT_MET",
                "text": "Còn giao dịch thanh toán chưa khớp hoặc đang mở liên quan tới đơn hàng của lô.",
            }

    # Hàng hoàn chờ duyệt
    draft_returns = ReturnToStock.objects.filter(
        batch=batch,
        status=ReturnToStock.Status.DRAFT,
    )
    if draft_returns.exists():
        return False, {
            "code": "AI_CLOSE_BATCH_CONDITIONS_NOT_MET",
            "text": "Còn phiếu hàng hoàn đang chờ duyệt tham chiếu lô.",
        }

    # 5. Việc AI đang PENDING hoặc SCHEDULED khác trên lô này
    from apps.ai.models import AiAction
    pending_ai_actions = AiAction.objects.filter(
        target_model__in=["batch", "Batch"],
        target_id__in=[str(batch.id), str(batch.batch_id)],
        status__in=[AiAction.Status.PENDING, AiAction.Status.SCHEDULED],
    )
    if current_action_id:
        pending_ai_actions = pending_ai_actions.exclude(pk=current_action_id)

    if pending_ai_actions.exists():
        return False, {
            "code": "AI_CLOSE_BATCH_CONDITIONS_NOT_MET",
            "text": "Còn việc AI khác đang chờ xử lý trên lô này.",
        }

    return True, None
