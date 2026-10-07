"""Guidance "chỉ dòng thời gian" cho mặt hàng (`item`) — Lô 2, R2 (02b §3.8). Không có giá bán hay giá vốn."""
from apps.catalog.models import Item
from apps.common.guidance.api import register_guidance
from apps.common.guidance.audit_timeline import make_audit_timeline_provider

ACTION_LABELS = {
    "item_image_add": "Thêm ảnh mặt hàng",
    "item_image_replace": "Thay ảnh mặt hàng",
    "item_image_remove": "Gỡ ảnh mặt hàng",
    "admin_edit": "Sửa trong trang quản trị kỹ thuật",
}

register_guidance(
    "item",
    make_audit_timeline_provider(
        Item,
        "catalog.view_item",
        doc_type="item",
        code_fn=lambda i: i.code,
        action_labels=ACTION_LABELS,
    ),
)
