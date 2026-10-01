"""
Tham số lọc của các danh sách danh mục & giá (R14, Lô 13): id, đúng/sai, một giá trị trong enum.

Quy ước chung của các danh sách console: rỗng (hoặc chỉ khoảng trắng) = không lọc; sai → 400 `INVALID_FILTER`,
thông điệp chỉ nêu TÊN tham số, không lặp lại giá trị người gọi gửi lên. Id không tồn tại → danh sách rỗng, không lỗi.
"""
from apps.common.exceptions import BusinessError
from apps.common.params import INVALID_FILTER, parse_positive_id

TRUE_VALUES = frozenset({"1", "true", "yes"})
FALSE_VALUES = frozenset({"0", "false", "no"})


def _invalid(message):
    return BusinessError(message, code=INVALID_FILTER)


def _raw(params, name):
    return (params.get(name) or "").strip()


def id_param(params, name):
    """Id nguyên dương, hoặc None khi không lọc."""
    raw = _raw(params, name)
    if not raw:
        return None
    try:
        return parse_positive_id(raw)
    except ValueError:
        raise _invalid(f"Tham số {name} phải là số nguyên dương.") from None


def bool_param(params, name):
    """True / False theo `1|true|yes` / `0|false|no` (không phân biệt hoa thường), hoặc None khi không lọc."""
    raw = _raw(params, name).lower()
    if not raw:
        return None
    if raw in TRUE_VALUES:
        return True
    if raw in FALSE_VALUES:
        return False
    raise _invalid(f"Tham số {name} phải là 1 hoặc 0.")


def choice_param(params, name, choices):
    """Một giá trị thuộc `choices`, hoặc None khi không lọc."""
    raw = _raw(params, name)
    if not raw:
        return None
    if raw not in set(choices):
        raise _invalid(f"Tham số {name} có giá trị không hợp lệ.")
    return raw
