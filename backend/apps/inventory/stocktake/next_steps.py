"""Guidance "chỉ dòng thời gian" cho phiếu kiểm kê (`stocktake`) — Lô 2, R2 (02b §3.8). Không có số tiền."""
from apps.common.guidance.api import register_guidance
from apps.common.guidance.audit_timeline import make_audit_timeline_provider
from apps.inventory.models import StockReconciliation

ACTION_LABELS = {
    "submit_stockreconciliation": "Gửi duyệt",
    "return_stockreconciliation_to_draft": "Trả về nháp để sửa",
    "approve_stockreconciliation": "Duyệt kiểm kê và cân đối sổ kho",
}

register_guidance(
    "stocktake",
    make_audit_timeline_provider(
        StockReconciliation,
        "inventory.view_stockreconciliation",
        doc_type="stocktake",
        code_fn=lambda r: f"KK-{r.pk}",
        action_labels=ACTION_LABELS,
        created_label="Nhập số kiểm kê",
        creator_attr="created_by",
    ),
)
