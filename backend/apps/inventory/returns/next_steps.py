"""Guidance "chỉ dòng thời gian" cho hàng hoàn về kho (`return`) — Lô 2, R2 (02b §3.8). Không có số tiền.

Phạm vi dòng (Lô 9): dùng CHUNG `scope_returns_for` với API `/api/inventory/returns/` — người giao chỉ xem được dòng thời
gian của phiếu hàng hoàn thuộc phiếu giao gán cho mình, ngoài ra 404.
"""
from apps.common.guidance.api import register_guidance
from apps.common.guidance.audit_timeline import make_audit_timeline_provider
from apps.inventory.models import ReturnToStock

from .scope import scope_returns_for

ACTION_LABELS = {
    "return_to_warehouse": "Mang hàng về kho",
    "approve_returntostock": "Duyệt hàng hoàn",
    "cancel_returntostock": "Huỷ phiếu hàng hoàn",
}

register_guidance(
    "return",
    make_audit_timeline_provider(
        ReturnToStock,
        "inventory.view_returntostock",
        scope_returns_for,
        doc_type="return",
        code_fn=lambda r: f"RT-{r.pk}",
        action_labels=ACTION_LABELS,
        created_label="Tạo phiếu hàng hoàn",
        creator_attr="created_by",
    ),
)
