"""
Truy vấn nhà cung cấp (B3, 02b §3 B3): số liệu tổng hợp và tham số lọc của danh sách.

Quy tắc đã chốt (Duy 01/10, Q4 ở 02-stories): chỉ phiếu `SUBMITTED` (Đã ghi nhận) được tính cho `receipt_count`,
`last_received_at` và `purchase_total`. Phiếu Nháp và Đã huỷ không tính. Muốn đổi thì sửa `COUNTED_STATUSES`.

`purchase_total` (tiền mua, giá vốn) tính bằng Decimal trong Python, mỗi dòng làm tròn 2 chữ số rồi mới cộng, đúng
cách `purchase_amount` của phiếu nhập (R10) nên hai màn khớp nhau. Một truy vấn cho cả trang, không N+1.

Lọc (quy ước chung của danh sách, xem `apps/inventory/stock/filters.py`): rỗng = không lọc; sai → 400
`INVALID_FILTER`, thông điệp chỉ nêu TÊN tham số, không lặp lại giá trị người gọi gửi lên.
"""
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Count, Max, Q

from apps.common.exceptions import BusinessError
from apps.inventory.stock.filters import INVALID_FILTER, parse_choice_list_param
from apps.purchasing.models import PurchaseReceipt, PurchaseReceiptLine, Supplier

from .filters import parse_bool_param

COUNTED_STATUSES = (PurchaseReceipt.Status.SUBMITTED,)
SEARCH_MAX_LENGTH = 100
CENT = Decimal("0.01")


def annotate_aggregates(queryset):
    """Thêm `receipt_count` và `last_received_at` (không join thêm bảng dòng nhập)."""
    counted = Q(receipts__status__in=COUNTED_STATUSES)
    return queryset.annotate(
        receipt_count=Count("receipts", filter=counted),
        last_received_at=Max("receipts__created_at", filter=counted),
    ).order_by("name", "id")


def attach_purchase_totals(suppliers):
    """Gắn `_purchase_total` (Decimal) vào từng nhà cung cấp trong `suppliers`, bằng đúng một truy vấn."""
    suppliers = list(suppliers)
    totals = {supplier.pk: Decimal("0") for supplier in suppliers}
    if totals:
        rows = PurchaseReceiptLine.objects.filter(
            receipt__supplier_id__in=totals, receipt__status__in=COUNTED_STATUSES
        ).values_list("receipt__supplier_id", "qty", "rate")
        for supplier_id, qty, rate in rows:
            totals[supplier_id] += (qty * rate).quantize(CENT, rounding=ROUND_HALF_UP)
    for supplier in suppliers:
        supplier._purchase_total = totals[supplier.pk]
    return suppliers


def matching_ids(search):
    """Id nhà cung cấp có tên hoặc SĐT chứa `search`, so khớp không phân biệt hoa thường theo Unicode.
    So trong Python (bảng nhà cung cấp nhỏ) vì `icontains` của SQLite chỉ phân biệt hoa thường với chữ ASCII,
    còn tiếng Việt có dấu thì không; làm thế này thì kết quả giống nhau ở mọi cơ sở dữ liệu."""
    needle = search.casefold()
    return [
        pk for pk, name, phone in Supplier.objects.values_list("pk", "name", "phone")
        if needle in name.casefold() or needle in phone.casefold()
    ]


def name_taken(name, *, exclude_pk=None):
    """Đã có nhà cung cấp khác trùng tên (không phân biệt hoa thường theo Unicode, bỏ khoảng trắng hai đầu)?"""
    wanted = name.strip().casefold()
    return any(
        existing.strip().casefold() == wanted
        for pk, existing in Supplier.objects.values_list("pk", "name") if pk != exclude_pk
    )


def filter_suppliers(queryset, params):
    """`q` (tên hoặc SĐT, không phân biệt hoa thường), `supplier_type` (nhiều, cách dấu phẩy), `is_active`."""
    search = (params.get("q") or "").strip()
    if len(search) > SEARCH_MAX_LENGTH:
        raise BusinessError("Tham số q quá dài.", code=INVALID_FILTER)
    if search:
        queryset = queryset.filter(pk__in=matching_ids(search))
    types = parse_choice_list_param(params, "supplier_type", Supplier.SupplierType.values)
    if types:
        queryset = queryset.filter(supplier_type__in=types)
    is_active = parse_bool_param(params, "is_active")
    if is_active is not None:
        queryset = queryset.filter(is_active=is_active)
    return queryset
