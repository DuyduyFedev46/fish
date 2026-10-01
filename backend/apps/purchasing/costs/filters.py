"""
Tham số lọc của danh sách chi phí phụ (R12, 02b §3.8): `cost_type` (nhiều, cách dấu phẩy), `month=YYYY-MM`
(theo `incurred_date`).

Quy ước chung của các danh sách (xem `apps/inventory/stock/filters.py`): rỗng = không lọc; sai → 400 `INVALID_FILTER`,
thông điệp chỉ nêu TÊN tham số, không lặp lại giá trị người gọi gửi lên.
"""
from apps.common.params import month_bounds
from apps.inventory.stock.filters import parse_choice_list_param
from apps.purchasing.models import PurchaseCost


def filter_costs(queryset, params):
    cost_types = parse_choice_list_param(params, "cost_type", PurchaseCost.CostType.values)
    if cost_types:
        queryset = queryset.filter(cost_type__in=cost_types)
    month = params.get("month") or ""  # không strip: "\n2026-10" phải bị từ chối
    if month:
        start, end = month_bounds(month)
        queryset = queryset.filter(incurred_date__gte=start.date(), incurred_date__lt=end.date())
    return queryset
