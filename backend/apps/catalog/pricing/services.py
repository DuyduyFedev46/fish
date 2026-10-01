"""
Giá niêm yết: giá hiệu lực cho Shop (BR-DM-02), đặt giá mới và sửa khoảng hiệu lực (BR-DM-03) — KHÔNG chứa giá vốn.
Trả None khi chưa có giá (Shop ẩn mặt hàng đó).
"""
import datetime

from django.db import transaction
from django.db.models import Prefetch, Q
from django.utils import timezone

from apps.catalog.models import ItemPrice, PriceList
from apps.common.audit import record_audit
from apps.common.exceptions import BusinessError

OVERLAP_CODE = "BR-DM-03"
ONE_DAY = datetime.timedelta(days=1)


# Thứ tự chọn giá hiệu lực: bảng giá mặc định trước, rồi giá bắt đầu muộn nhất, rồi giá tạo sau cùng.
EFFECTIVE_ORDER = ("-price_list__is_default", "-valid_from", "-id")
CURRENT_PRICES_ATTR = "current_prices"


def _in_effect(queryset, on_date):
    return queryset.filter(valid_from__lte=on_date).filter(
        Q(valid_upto__isnull=True) | Q(valid_upto__gte=on_date)
    )


def current_item_price(item, on_date=None):
    """`ItemPrice` hiệu lực của mặt hàng (BR-DM-02), hoặc None. Nguồn chung cho Shop và ERP (R14)."""
    on_date = on_date or timezone.localdate()
    return _in_effect(ItemPrice.objects.filter(item=item), on_date).order_by(*EFFECTIVE_ORDER).first()


def effective_price(item, on_date=None):
    price = current_item_price(item, on_date)
    return price.rate if price else None


def prefetch_current_prices(on_date=None):
    """`Prefetch` cho danh sách mặt hàng: mỗi mặt hàng có `current_prices` (giá hiệu lực, giá thắng đứng đầu),
    để danh sách không phải hỏi DB từng dòng (R14)."""
    on_date = on_date or timezone.localdate()
    return Prefetch(
        "prices",
        queryset=_in_effect(ItemPrice.objects.all(), on_date).order_by(*EFFECTIVE_ORDER),
        to_attr=CURRENT_PRICES_ATTR,
    )


def _overlaps(start_a, end_a, start_b, end_b):
    """Hai khoảng [start, end] (end None = vô hạn) có chung ngày nào không."""
    return (end_b is None or start_a <= end_b) and (end_a is None or start_b <= end_a)


def _lock_price_lists(price_list_ids):
    """Khoá dòng bảng giá (theo id tăng dần) — luôn là bước ĐẦU, ở cả POST lẫn PATCH, để hai thao tác cùng lúc
    xếp hàng theo cùng một thứ tự (không deadlock). Khoá cả bảng giá vì mặt hàng chưa có giá nào thì không có
    dòng giá để khoá."""
    return list(PriceList.objects.select_for_update().filter(pk__in=price_list_ids).order_by("pk"))


def _lock_item_prices(*, price_list, item):
    return list(ItemPrice.objects.select_for_update().filter(price_list=price_list, item=item))


def _lock_price_row(pk):
    return ItemPrice.objects.select_for_update().get(pk=pk)


def _overlap_error():
    return BusinessError(
        "Khoảng hiệu lực chồng lấn với một giá đã có của mặt hàng này (BR-DM-03). "
        "Chọn ngày bắt đầu sau ngày bắt đầu của giá đang áp dụng, hoặc sửa giá hiện có.",
        code=OVERLAP_CODE,
    )


def _tail_gap_error():
    return BusinessError(
        "Giá đang áp dụng còn hiệu lực sau ngày kết thúc bạn chọn, nếu đặt thì sau ngày đó mặt hàng không còn giá (BR-DM-03). "
        "Hãy để trống \"đến ngày\", hoặc chọn ngày kết thúc không ngắn hơn giá đang áp dụng.",
        code=OVERLAP_CODE,
    )


@transaction.atomic
def set_item_price(*, price_list, item, rate, valid_from, valid_upto=None, actor):
    """Đặt giá mới cho mặt hàng trong một bảng giá (ED-31-AC1, BR-DM-02/03).

    Giá đang hiệu lực tại `valid_from` (bắt đầu sớm hơn và còn hiệu lực tới ngày đó) được đóng bằng
    `valid_upto = valid_from − 1 ngày`. Nếu khoảng mới chồng lên một giá bắt đầu cùng ngày hoặc muộn hơn
    (giá tương lai) thì 400 mã `BR-DM-03`; không tự sửa hay xoá giá đó. Ghi audit `create_itemprice`
    và `close_itemprice` cho từng giá bị đóng.
    """
    _lock_price_lists([price_list.pk])
    existing = _lock_item_prices(price_list=price_list, item=item)
    to_close = []
    for other in existing:
        if not _overlaps(valid_from, valid_upto, other.valid_from, other.valid_upto):
            continue
        if other.valid_from >= valid_from:
            raise _overlap_error()
        if valid_upto is not None and (other.valid_upto is None or other.valid_upto > valid_upto):
            # Đóng giá cũ ở valid_from − 1 sẽ cắt mất đuôi của nó: sau valid_upto mới mặt hàng không còn giá.
            raise _tail_gap_error()
        to_close.append(other)

    new_price = ItemPrice.objects.create(
        price_list=price_list, item=item, rate=rate, valid_from=valid_from, valid_upto=valid_upto
    )
    record_audit(
        "create_itemprice", actor=actor, obj=new_price,
        changes={
            "item": item.pk, "item_code": item.code, "price_list": price_list.pk,
            "valid_from": valid_from, "valid_upto": valid_upto, "sell_rate": rate,
        },
    )
    for old in to_close:
        previous_end = old.valid_upto
        old.valid_upto = valid_from - ONE_DAY
        old.save(update_fields=["valid_upto"])
        record_audit(
            "close_itemprice", actor=actor, obj=old,
            changes={"valid_upto": {"from": previous_end, "to": old.valid_upto}, "replaced_by": new_price.pk},
        )
    return new_price


@transaction.atomic
def update_item_price(*, price, changes, actor):
    """Sửa giá niêm yết đã có (PATCH). Đổi ngày, mặt hàng hay bảng giá thì kiểm chồng lấn (BR-DM-03) với các
    giá khác; chỉ đổi đơn giá thì không kiểm, nên dữ liệu cũ đã chồng lấn vẫn sửa được đơn giá."""
    # Cùng thứ tự khoá với set_item_price: bảng giá trước, dòng giá sau.
    price = ItemPrice.objects.get(pk=price.pk)
    target_list = changes.get("price_list", price.price_list)
    _lock_price_lists({price.price_list_id, target_list.pk})
    price = _lock_price_row(price.pk)
    new_values = {name: changes.get(name, getattr(price, name)) for name in ("price_list", "item", "valid_from", "valid_upto")}
    scope_changed = any(
        new_values[name] != getattr(price, name) for name in ("price_list", "item", "valid_from", "valid_upto")
    )
    if scope_changed:
        for other in _lock_item_prices(price_list=new_values["price_list"], item=new_values["item"]):
            if other.pk != price.pk and _overlaps(
                new_values["valid_from"], new_values["valid_upto"], other.valid_from, other.valid_upto
            ):
                raise _overlap_error()
    diff = {}
    for name, value in changes.items():
        old_value = getattr(price, name)
        if value != old_value:
            key = "sell_rate" if name == "rate" else name
            diff[key] = {
                "from": old_value.pk if hasattr(old_value, "pk") else old_value,
                "to": value.pk if hasattr(value, "pk") else value,
            }
            setattr(price, name, value)
    if diff:
        price.save()
        record_audit("update_itemprice", actor=actor, obj=price, changes=diff)
    return price
