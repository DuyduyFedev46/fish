"""
Guidance "chỉ dòng thời gian" cho khách hàng (`customer`) — Lô 2, R2 (02b §3.8).

Quyền: `sales.view_customer_list` (quyền Tầng 2, B2/Lô 6) qua hàm chung `can_view_customer_directory`
(`apps/sales/customers/permissions.py`), cùng hàm với danh bạ khách và lọc đơn theo khách.

Bất biến 9: dòng thời gian chỉ có việc + nhân viên làm + giờ; tuyệt đối không tên, SĐT, địa chỉ, ghi chú khách,
không `object_repr` (chứa tên + SĐT). Response gắn `Cache-Control: no-store`.
"""
from apps.common.guidance.api import register_guidance
from apps.common.guidance.audit_timeline import make_audit_timeline_provider
from apps.sales.customers.permissions import can_view_customer_directory
from apps.sales.models import Customer

ACTION_LABELS = {
    "update_customer": "Cập nhật hồ sơ khách",
    "customer_anonymize": "Ẩn danh hoá hồ sơ khách",
    "admin_edit": "Sửa trong trang quản trị kỹ thuật",
}


register_guidance(
    "customer",
    make_audit_timeline_provider(
        Customer,
        can_view_customer_directory,
        doc_type="customer",
        code_fn=lambda c: f"KH-{c.pk}",
        action_labels=ACTION_LABELS,
        created_label="Tạo hồ sơ khách",
        no_store=True,
    ),
)
