"""
Tham số lọc của danh sách hoá đơn mua (R11, 02b §3.8): `is_paid=1|0|true|false`, `supplier=<id>`, `month=YYYY-MM`
(theo `invoice_date`).

Quy ước chung của các danh sách (xem `apps/inventory/stock/filters.py`): rỗng = không lọc; sai → 400 `INVALID_FILTER`,
thông điệp chỉ nêu TÊN tham số, không lặp lại giá trị người gọi gửi lên.
"""
from apps.common.params import month_bounds
from apps.inventory.stock.filters import parse_id_param
from apps.purchasing.receipts.filters import parse_bool_param


def filter_invoices(queryset, params):
    is_paid = parse_bool_param(params, "is_paid")
    if is_paid is not None:
        queryset = queryset.filter(is_paid=is_paid)
    supplier = parse_id_param(params, "supplier")
    if supplier is not None:
        queryset = queryset.filter(supplier_id=supplier)
    month = params.get("month") or ""  # không strip: "\n2026-10" phải bị từ chối
    if month:
        start, end = month_bounds(month)
        queryset = queryset.filter(invoice_date__gte=start.date(), invoice_date__lt=end.date())
    return queryset
