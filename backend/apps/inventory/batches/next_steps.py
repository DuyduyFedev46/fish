"""
Xác định các bước tiếp theo (NextStep) và cung cấp Guidance cho Lô hàng (Batch).

Bất biến:
- Một nguồn cho cả guidance, available_actions và service check.
- Không rò giá vốn: lọc giá vốn theo quyền viewer (DW-05-AC3, Bất biến 1).
- Không rò PII khách (DW-05-AC6, Bất biến 9).
- T1 view_batch giống hệt BatchViewSet (DW-05-AC5).
"""
import datetime
from typing import Any, Optional

from django.conf import settings
from django.http import Http404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.common.cost_keys import can_view_cost
from apps.common.guidance.api import register_guidance
from apps.common.guidance.reasons import get_reason
from apps.common.guidance.steps import Missing, NextStep, Why, step_to_dict
from apps.common.guidance.timeline import format_guidance_timeline
from apps.inventory.batches.services import check_close_batch
from apps.inventory.batches.timeline import build_batch_timeline
from apps.inventory.models import Batch


def get_batch_next_steps(batch: Batch, user: Any) -> list[NextStep]:
    """
    Trả danh sách NextStep cho lô hàng dựa trên trạng thái và quyền của user.
    """
    steps: list[NextStep] = []

    # 1. Bước mở bán khi DRAFT
    if batch.status == Batch.Status.DRAFT:
        can_publish = user.has_perm("inventory.publish_batch")
        steps.append(
            NextStep(
                key="publish",
                label="Mở bán lô",
                actor="user",
                allowed=can_publish,
                who=["Quản lý", "Chủ"],
                missing=[] if can_publish else [Missing("BR-PQ-12", get_reason("BR-PQ-12"))],
                deadline=None,
                why=Why("BR-LO-02", "Mở bán lô để bắt đầu nhận đơn giữ chỗ"),
                command="inventory.batch.publish",
                ai=None,
            )
        )

    # 2. Bước hệ thống khi SELLING hoặc NEAR_EXPIRY
    if batch.status in (Batch.Status.SELLING, Batch.Status.NEAR_EXPIRY):
        near_days = getattr(settings, "BATCH_NEAR_EXPIRY_DAYS", 14)
        today = timezone.localdate()
        days_to_expiry = (batch.expiry_date - today).days

        # DW-05-AC1: Lô SELLING, hạn dùng còn <= NEAR_EXPIRY_DAYS: bước hệ thống "chuyển Cận hạn"
        if batch.status == Batch.Status.SELLING and days_to_expiry <= near_days:
            steps.append(
                NextStep(
                    key="auto_near_expiry",
                    label="Hệ thống sẽ chuyển Cận hạn",
                    actor="system",
                    allowed=False,
                    who=["Hệ thống"],
                    missing=[],
                    deadline=f"{batch.expiry_date}T00:00:00+07:00",
                    why=Why("BR-LO-06", get_reason("BR-LO-06")),
                    command=None,
                    ai=None,
                )
            )

        # Bước hệ thống chuyển Quá hạn
        steps.append(
            NextStep(
                key="auto_expire",
                label="Hệ thống sẽ chuyển Quá hạn",
                actor="system",
                allowed=False,
                who=["Hệ thống"],
                missing=[],
                deadline=f"{batch.expiry_date}T00:00:00+07:00",
                why=Why("BR-LO-02", get_reason("BR-LO-02")),
                command=None,
                ai=None,
            )
        )

    # 3. Bước huỷ lô khi EXPIRED (DW-06, BR-LO-03)
    if batch.status == Batch.Status.EXPIRED:
        can_cancel = user.has_perm("inventory.cancel_expired_batch")
        missing_perm = [] if can_cancel else [Missing("BR-PQ-12", get_reason("BR-PQ-12"))]
        steps.append(
            NextStep(
                key="cancel_expired",
                label="Huỷ lô",
                actor="user",
                allowed=can_cancel,
                who=["Chủ"],
                missing=missing_perm,
                deadline=None,
                why=Why("BR-LO-03", get_reason("BR-LO-03")),
                command="inventory.batch.cancel_expired",
                ai=None,
            )
        )

    # 4. Bước chốt lô (close) khi lô chưa chốt và không ở trạng thái EXPIRED (khi EXPIRED thì bước tiếp là huỷ lô)
    if not batch.is_closed and batch.status != Batch.Status.EXPIRED:
        missing_biz = check_close_batch(batch)
        can_close = user.has_perm("inventory.close_batch")
        missing_perm = [] if can_close else [Missing("BR-PQ-12", get_reason("BR-PQ-12"))]
        all_missing = missing_biz + missing_perm
        allowed = (len(missing_biz) == 0) and can_close

        steps.append(
            NextStep(
                key="close",
                label="Chốt lô",
                actor="user",
                allowed=allowed,
                who=["Chủ"],
                missing=all_missing,
                deadline=None,
                why=Why("BR-LO-04", get_reason("BR-LO-04")),
                command="inventory.batch.close",
                ai=None,
            )
        )

    return steps


def get_batch_guidance(doc_id: str, user: Any, request: Optional[Any] = None) -> dict[str, Any]:
    """
    Guidance provider cho loại chứng từ "batch".
    """
    # DW-05-AC5: nv_giao nhận 403
    if not user.has_perm("inventory.view_batch"):
        raise PermissionDenied("Bạn không có quyền xem lô hàng.")

    qs = Batch.objects.select_related(
        "item",
        "supplier",
        "warehouse",
        "closed_by__staff_profile",
    ).prefetch_related("cost_allocations")

    try:
        if str(doc_id).isdigit():
            batch = qs.get(pk=int(doc_id))
        else:
            batch = qs.get(batch_id=doc_id)
    except Batch.DoesNotExist:
        raise Http404(f"Không tìm thấy lô hàng: {doc_id}")

    doc_summary = {
        "type": "batch",
        "id": batch.pk,
        "code": batch.batch_id,
        "status": batch.status,
        "status_label": batch.get_status_display(),
    }

    next_steps_objs = get_batch_next_steps(batch, user)
    next_steps_data = [step_to_dict(s, user=user) for s in next_steps_objs]

    timeline_events = build_batch_timeline(batch, viewer=user)
    timeline_data = format_guidance_timeline(timeline_events, viewer=user)

    # DW-05-AC4: Cảnh báo lô chưa có chi phí mua không kèm số tiền
    warnings: list[dict[str, Any]] = []
    if batch.cost_allocations.count() == 0:
        warnings.append({
            "code": "GW-01",
            "text": "Lô chưa có chi phí mua nào (có thể thiếu đá, xe)",
        })

    related: list[dict[str, str]] = []
    try:
        from apps.sales.models import SalesOrderLineBatch
        order_codes = (
            SalesOrderLineBatch.objects.filter(batch=batch)
            .values_list("order_line__order__code", flat=True)
            .distinct()[:5]
        )
        for code in order_codes:
            if code:
                related.append({"type": "order", "code": code})
    except Exception:
        pass

    return {
        "doc": doc_summary,
        "next_steps": next_steps_data,
        "warnings": warnings,
        "timeline": timeline_data,
        "related": related,
    }


# Đăng ký tự động provider
register_guidance("batch", get_batch_guidance)
