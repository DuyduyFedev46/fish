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


def apply_item_filters(qs, params):
    """
    Bốn bộ lọc danh sách mặt hàng (R14): `item_group=<id>`, `is_active=1|0`, `item_type=SIMPLE|BUNDLE`, `has_image=1|0`.
    Rỗng = không lọc; sai → 400 INVALID_FILTER. Dùng chung cho danh sách và tải file Excel (FISH-66 S3-AC6).
    """
    from apps.catalog.models import Item

    group = id_param(params, "item_group")
    if group is not None:
        qs = qs.filter(item_group_id=group)
    is_active = bool_param(params, "is_active")
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    has_image = bool_param(params, "has_image")  # A2-AC16; sai giá trị → 400 như các bộ lọc khác (L5)
    if has_image is not None:
        qs = qs.filter(image__isnull=not has_image)
    item_type = choice_param(params, "item_type", Item.ItemType.values)
    if item_type is not None:
        qs = qs.filter(item_type=item_type)
    return qs
