"""
Giá niêm yết hiệu lực cho Shop (BR-DM-02) — KHÔNG chứa giá vốn.
Trả None khi chưa có giá (Shop ẩn mặt hàng đó).
"""
from django.db.models import Q
from django.utils import timezone

from apps.catalog.models import ItemPrice


def effective_price(item, on_date=None):
    on_date = on_date or timezone.localdate()
    price = (
        ItemPrice.objects.filter(item=item, valid_from__lte=on_date)
        .filter(Q(valid_upto__isnull=True) | Q(valid_upto__gte=on_date))
        .order_by("-price_list__is_default", "-valid_from", "-id")
        .first()
    )
    return price.rate if price else None
