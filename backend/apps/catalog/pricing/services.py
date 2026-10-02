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
PRICE_USED_CODE = "PRICE_USED_BY_ORDERS"
PRICE_USED_MESSAGE = (
    "Giá này đã áp vào đơn hàng, không sửa được. "
    "Hãy đặt giá mới bắt đầu từ ngày mai. Muốn ngừng bán ngay thì tạm ẩn mặt hàng."
)
ONE_DAY = datetime.timedelta(days=1)
FAR_FUTURE = datetime.date.max


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


def _price_used_error():
    return BusinessError(PRICE_USED_MESSAGE, code=PRICE_USED_CODE)


def _order_days(item, start, end):
    """Các ngày (giờ VN) trong [start, end] (end None = vô hạn) có đơn hàng chứa `item`, mọi trạng thái đơn.
    `SalesOrderLine` không giữ khoá tới `ItemPrice`/bảng giá nên "đã áp vào đơn" suy ra từ ngày tạo đơn + mặt hàng."""
    from apps.sales.models import SalesOrderLine  # nhập muộn: tránh vòng catalog <-> sales

    tz = timezone.get_current_timezone()
    lines = SalesOrderLine.objects.filter(item=item)
    lines = lines.filter(order__created_at__gte=datetime.datetime.combine(start, datetime.time.min, tzinfo=tz))
    if end is not None and end < FAR_FUTURE:
        lines = lines.filter(
            order__created_at__lt=datetime.datetime.combine(end + ONE_DAY, datetime.time.min, tzinfo=tz)
        )
    stamps = lines.values_list("order__created_at", flat=True).distinct()
    return {timezone.localtime(stamp, tz).date() for stamp in stamps}


def _covered_by_default_list(item, day, *, exclude_pk=None):
    prices = _in_effect(ItemPrice.objects.filter(item=item, price_list__is_default=True), day)
    if exclude_pk is not None:
        prices = prices.exclude(pk=exclude_pk)
    return prices.exists()


def _window_used_by_orders(*, price_list, item, start, end, exclude_pk=None):
    """Có đơn nào chốt giá trong [start, end] cho `item` mà giá của `price_list` đang quyết định không.
    Đơn lấy bảng giá mặc định trước (`EFFECTIVE_ORDER`): ngày mà bảng mặc định đã có giá thì giá ở bảng khác
    không phải là giá đã áp vào đơn."""
    for day in _order_days(item, start, end):
        if price_list.is_default or not _covered_by_default_list(item, day, exclude_pk=exclude_pk):
            return True
    return False


def _date_window_difference(old_start, old_end, new_start, new_end):
    """Các khoảng ngày mà mức phủ thay đổi khi cửa sổ [old] thành [new] (hiệu đối xứng). Hai khoảng rời nhau
    thì trả cả hai khoảng."""
    old_end_v, new_end_v = old_end or FAR_FUTURE, new_end or FAR_FUTURE
    if old_start > new_end_v or new_start > old_end_v:
        return [(old_start, old_end), (new_start, new_end)]
    pieces = []
    if old_start != new_start:
        pieces.append((min(old_start, new_start), max(old_start, new_start) - ONE_DAY))
    if old_end_v != new_end_v:
        low = min(old_end_v, new_end_v)
        pieces.append((low + ONE_DAY, None if max(old_end_v, new_end_v) == FAR_FUTURE else max(old_end_v, new_end_v)))
    return pieces


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

    if valid_from < timezone.localdate() and _window_used_by_orders(
        price_list=price_list, item=item, start=valid_from, end=valid_upto
    ):
        # Đặt giá lùi ngày sẽ đổi giá hiệu lực của những ngày đã có đơn chốt giá (BR-DM-02).
        raise _price_used_error()

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


def _edit_hits_orders(price, new_values, *, rate_changed):
    """Sửa `price` thành `new_values` có làm đổi giá của ngày nào đã có đơn chốt giá không.
    Đổi đơn giá, mặt hàng hay bảng giá: cả khoảng cũ và khoảng mới. Chỉ đổi ngày: phần ngày bị thêm hoặc bớt."""
    same_target = new_values["item"] == price.item and new_values["price_list"] == price.price_list
    if rate_changed or not same_target:
        windows = [
            (price.price_list, price.item, price.valid_from, price.valid_upto),
            (new_values["price_list"], new_values["item"], new_values["valid_from"], new_values["valid_upto"]),
        ]
    else:
        windows = [
            (price.price_list, price.item, start, end)
            for start, end in _date_window_difference(
                price.valid_from, price.valid_upto, new_values["valid_from"], new_values["valid_upto"]
            )
        ]
    return any(
        _window_used_by_orders(price_list=plist, item=item, start=start, end=end, exclude_pk=price.pk)
        for plist, item, start, end in windows
    )


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
    changed = {name for name, value in changes.items() if value != getattr(price, name)}
    if changed and _edit_hits_orders(price, new_values, rate_changed="rate" in changed):
        raise _price_used_error()
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
