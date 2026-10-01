"""
Tham số lọc của danh sách phiếu nhập (R10): `status` (nhiều, cách dấu phẩy), `supplier=<id>`, `month=YYYY-MM`,
`date_from`/`date_to` (theo `received_date`), `has_invoice=1|0|true|false`.

Quy ước chung của các danh sách (xem `apps/inventory/stock/filters.py`): rỗng = không lọc; sai → 400 `INVALID_FILTER`,
thông điệp chỉ nêu TÊN tham số, không lặp lại giá trị người gọi gửi lên.
"""
import datetime
import re

from django.db.models import Exists, OuterRef

from apps.common.exceptions import BusinessError
from apps.inventory.stock.filters import (
    INVALID_FILTER, parse_choice_list_param, parse_date_param, parse_id_param,
)
from apps.purchasing.models import PurchaseInvoice, PurchaseReceipt

MONTH_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}")  # ASCII; fullmatch nên không nhận "\n" cuối
MONTH_MIN_YEAR, MONTH_MAX_YEAR = 2000, 2100
TRUE_VALUES = {"1", "true"}
FALSE_VALUES = {"0", "false"}


def month_range(raw):
    """`YYYY-MM` → (ngày đầu tháng, ngày đầu tháng sau). Sai dạng hoặc ngoài biên năm → 400 `INVALID_FILTER`."""
    try:
        if not MONTH_PATTERN.fullmatch(raw):
            raise ValueError
        year, month = int(raw[:4]), int(raw[5:])
        if not MONTH_MIN_YEAR <= year <= MONTH_MAX_YEAR:
            raise ValueError
        return datetime.date(year, month, 1), datetime.date(year + (month == 12), month % 12 + 1, 1)
    except ValueError:
        raise BusinessError("Tham số month phải có dạng YYYY-MM.", code=INVALID_FILTER) from None


def parse_bool_param(params, name):
    """True/False, hoặc None khi không truyền."""
    raw = (params.get(name) or "").strip()
    if not raw:
        return None
    if raw in TRUE_VALUES:
        return True
    if raw in FALSE_VALUES:
        return False
    raise BusinessError(f"Tham số {name} chỉ nhận 1 hoặc 0.", code=INVALID_FILTER)


def filter_list(queryset, params):
    statuses = parse_choice_list_param(params, "status", PurchaseReceipt.Status.values)
    if statuses:
        queryset = queryset.filter(status__in=statuses)
    supplier = parse_id_param(params, "supplier")
    if supplier is not None:
        queryset = queryset.filter(supplier_id=supplier)
    month = params.get("month") or ""  # không strip: "\n2026-10" phải bị từ chối
    if month:
        start, end = month_range(month)
        queryset = queryset.filter(received_date__gte=start, received_date__lt=end)
    date_from = parse_date_param(params, "date_from")
    if date_from:
        queryset = queryset.filter(received_date__gte=date_from)
    date_to = parse_date_param(params, "date_to")
    if date_to:
        queryset = queryset.filter(received_date__lte=date_to)
    has_invoice = parse_bool_param(params, "has_invoice")
    if has_invoice is not None:
        # Exists, không join: hai hoá đơn của cùng phiếu không làm lặp dòng.
        has = Exists(PurchaseInvoice.objects.filter(receipt_id=OuterRef("pk")))
        queryset = queryset.filter(has if has_invoice else ~has)
    return queryset
