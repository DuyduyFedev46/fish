"""
Guidance "chỉ dòng thời gian" cho phiếu nhập (`receipt`) và nhà cung cấp (`supplier`) — Lô 2, R2 (02b §3.8).

Quyền đọc theo quyền xem chính đối tượng (`view_purchasereceipt` / `view_supplier`); phiếu nhập còn theo phạm vi D6
(`scope_receipts_for`, PV-06): ngoài phạm vi là 404 như chi tiết. Nhãn dòng không chứa giá,
số tiền hay tên nhà cung cấp; không đưa `AuditLog.note`/`changes` ra ngoài.
"""
from apps.common.guidance.api import register_guidance
from apps.common.guidance.audit_timeline import make_audit_timeline_provider
from apps.purchasing.models import PurchaseReceipt, Supplier

from .scope import scope_receipts_for

RECEIPT_ACTION_LABELS = {
    "create_and_submit_receipt": "Ghi nhận phiếu nhập và nhập lô",
    "cancel_purchase_receipt": "Huỷ phiếu nhập",
}

SUPPLIER_ACTION_LABELS = {
    "supplier_create": "Thêm nhà cung cấp",
    "supplier_update": "Cập nhật nhà cung cấp",
    "admin_edit": "Sửa trong trang quản trị kỹ thuật",
}

register_guidance(
    "receipt",
    make_audit_timeline_provider(
        PurchaseReceipt,
        "purchasing.view_purchasereceipt",
        scope_receipts_for,
        doc_type="receipt",
        code_fn=lambda r: f"PR-{r.pk}",
        action_labels=RECEIPT_ACTION_LABELS,
        created_label="Tạo phiếu nhập",
        creator_attr="created_by",
    ),
)

register_guidance(
    "supplier",
    make_audit_timeline_provider(
        Supplier,
        "purchasing.view_supplier",
        doc_type="supplier",
        code_fn=lambda s: f"SUP-{s.pk}",
        action_labels=SUPPLIER_ACTION_LABELS,
    ),
)
