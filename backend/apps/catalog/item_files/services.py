"""
Dịch vụ tải file Excel mặt hàng (FISH-66 S3, S4; BR-DM-27/28, BR-PQ-04/05).

Chỉ đọc `Item`, `ItemGroup`, `ItemPrice` — không join `Batch`/`PurchaseReceiptLine`, nên file không thể chứa giá vốn.
Số truy vấn cố định theo số món (S3-AC13): 1 truy vấn món (kèm nhóm) + 1 truy vấn giá khi có quyền xem giá.
"""
import datetime

from django.utils import timezone

from apps.catalog.items.filters import apply_item_filters
from apps.catalog.models import Item
from apps.catalog.pricing.services import CURRENT_PRICES_ATTR, prefetch_current_prices
from apps.common.audit import record_audit

from .columns import VIEW_PRICES_PERM, columns_for
from .workbook import build_items_workbook

TEMPLATE_FILENAME = "mau-hang-ban.xlsx"
TEMPLATE_EXAMPLE_CODE = "VD-001"  # dòng ví dụ; lô 3 chặn nhập mã này (S4-AC2)


def can_see_prices(user):
    return bool(user and user.has_perm(VIEW_PRICES_PERM))


def export_filename(now=None):
    """Tên file theo giờ Việt Nam: hang-ban-YYYYMMDD-HHmm.xlsx."""
    return timezone.localtime(now).strftime("hang-ban-%Y%m%d-%H%M.xlsx")


def _item_row(item, *, with_prices):
    row = {
        "code": item.code,
        "name": item.name,
        "item_group": item.item_group.name,
        "item_type": item.get_item_type_display(),
        "stock_uom": item.stock_uom,
        "is_active": item.is_active,
        "shelf_life_in_days": item.shelf_life_in_days,
        "has_batch_no": item.has_batch_no,
        "has_expiry_date": item.has_expiry_date,
        "short_note": item.short_note,
        "spec": item.spec,
        "storage": item.storage,
        "origin": item.origin,
        "description": item.description,
    }
    if with_prices:
        prices = getattr(item, CURRENT_PRICES_ATTR, None) or []
        row["current_price"] = prices[0].rate if prices else None
    return row


def export_items(*, user, params):
    """Trả `(bytes xlsx, số món)`; ghi AuditLog `export_items` chỉ có số đếm (không tên món, không bộ lọc)."""
    with_prices = can_see_prices(user)
    queryset = Item.objects.select_related("item_group").order_by("code")
    queryset = apply_item_filters(queryset, params)  # sai bộ lọc → BusinessError INVALID_FILTER, chưa ghi nhật ký
    if with_prices:
        queryset = queryset.prefetch_related(prefetch_current_prices())
    rows = [_item_row(item, with_prices=with_prices) for item in queryset]
    content = build_items_workbook(columns_for(with_prices=with_prices), rows)
    record_audit("export_items", actor=user, changes={"rows": len(rows), "with_prices": with_prices})
    return content, len(rows)


def export_template(*, user):
    """File mẫu: cùng bộ cột theo quyền, một dòng ví dụ GIẢ. Không đọc DB, không ghi nhật ký."""
    with_prices = can_see_prices(user)
    example = {
        "code": TEMPLATE_EXAMPLE_CODE,
        "name": "Cá ví dụ",
        "item_group": "Nhóm ví dụ",
        "item_type": Item.ItemType.SIMPLE.label,
        "stock_uom": "Kg",
        "is_active": True,
        "shelf_life_in_days": 365,
        "has_batch_no": True,
        "has_expiry_date": True,
    }
    if with_prices:
        example["new_price"] = 150000
        example["new_price_from"] = timezone.localdate() + datetime.timedelta(days=1)
    return build_items_workbook(columns_for(with_prices=with_prices), [example]), 1
