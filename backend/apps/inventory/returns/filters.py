"""
Tham số lọc của danh sách hàng hoàn (R9): `status` (nhiều, cách dấu phẩy) và `month=YYYY-MM` (theo ngày tạo, giờ VN).

Quy ước chung của các danh sách (xem `apps/inventory/stock/filters.py`): rỗng = không lọc; sai → 400 `INVALID_FILTER`,
thông điệp chỉ nêu TÊN tham số, không lặp lại giá trị người gọi gửi lên.
"""
from apps.common.params import month_bounds
from apps.inventory.models import ReturnToStock
from apps.inventory.stock.filters import parse_choice_list_param


def filter_list(queryset, params):
    statuses = parse_choice_list_param(params, "status", ReturnToStock.Status.values)
    if statuses:
        queryset = queryset.filter(status__in=statuses)
    month = params.get("month") or ""  # không strip: "\n2026-10" phải bị từ chối
    if month:
        start, end = month_bounds(month)
        queryset = queryset.filter(created_at__gte=start, created_at__lt=end)
    return queryset
