"""
Đọc và kiểm tham số lọc cho các danh sách kho (lô, sổ nhập xuất, phiếu điều chỉnh).

Quy ước (giống `apps/sales/orders/api.py`, `apps/delivery/api.py`):
- Tham số rỗng (hoặc chỉ khoảng trắng) nghĩa là không lọc.
- Sai định dạng → `BusinessError` mã `INVALID_FILTER`, `exception_handler` đổi thành 400 `{"detail","code"}`.
- Thông điệp chỉ nêu TÊN tham số, không lặp lại giá trị người gọi gửi lên.
- Id đi qua `apps/common/params.py::parse_positive_id` (chỉ chữ số ASCII, không quá int64).
"""
import datetime
import re

from django.db.models import Q

from apps.common.exceptions import BusinessError
from apps.common.params import parse_positive_id

INVALID_FILTER = "INVALID_FILTER"
_ISO_DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


def _invalid(message):
    return BusinessError(message, code=INVALID_FILTER)


def _raw(params, name):
    return (params.get(name) or "").strip()


def parse_id_param(params, name):
    """Id nguyên dương, hoặc None khi không truyền."""
    raw = _raw(params, name)
    if not raw:
        return None
    try:
        return parse_positive_id(raw)
    except ValueError:
        raise _invalid(f"Tham số {name} phải là số nguyên dương.") from None


def parse_date_param(params, name):
    """Ngày dạng YYYY-MM-DD, hoặc None khi không truyền."""
    raw = _raw(params, name)
    if not raw:
        return None
    if not _ISO_DATE.match(raw):
        raise _invalid(f"Tham số {name} phải là ngày dạng YYYY-MM-DD.")
    try:
        return datetime.date.fromisoformat(raw)
    except ValueError:
        raise _invalid(f"Tham số {name} phải là ngày dạng YYYY-MM-DD.") from None


def parse_choice_list_param(params, name, choices):
    """Một hoặc nhiều giá trị cách nhau dấu phẩy, mỗi giá trị phải thuộc `choices`. Trả list (rỗng = không lọc)."""
    raw = _raw(params, name)
    if not raw:
        return []
    values = [part.strip() for part in raw.split(",") if part.strip()]
    allowed = set(choices)
    if any(value not in allowed for value in values):
        raise _invalid(f"Tham số {name} có giá trị không hợp lệ.")
    return values


def date_range_q(params, field):
    """Khoảng ngày `date_from`/`date_to` (gồm cả hai đầu) theo ngày giờ Việt Nam (TIME_ZONE) của cột `field`."""
    cond = Q()
    date_from = parse_date_param(params, "date_from")
    date_to = parse_date_param(params, "date_to")
    if date_from:
        cond &= Q(**{f"{field}__date__gte": date_from})
    if date_to:
        cond &= Q(**{f"{field}__date__lte": date_to})
    return cond
