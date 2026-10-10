"""
Khối JSON dùng chung của tạo đơn và tra đơn Shop (02b §3.3, §3.4). Dict dựng tường minh, KHÔNG serializer back-office.

Không bao giờ có: tên, SĐT, địa chỉ khách, `cancel_note`, ghi chú nhân viên, mã lô, ngày nhập, giá vốn (bất biến 1 và 9).
"""
from django.conf import settings

from apps.catalog.items.services import sale_unit
from apps.common.formatting import iso_utc
from apps.sales.models import SalesOrder
from apps.sales.utils import ZERO, money_str, money_vnd

from .lookup_token import make_token


def lines_payload(order):
    """`amount` là thành tiền GỘP (qty × đơn giá, trước giảm) — khớp 02b §3.3."""
    rows = []
    for line in order.lines.select_related("item").order_by("pk"):
        rows.append(
            {
                "item_code": line.item.code,
                "name": line.item.name,
                "unit": sale_unit(line.item),
                "qty": money_str(line.qty),
                "amount": money_str(money_vnd(line.amount + line.discount_amount)),
            }
        )
    return rows


def money_block(order):
    """`subtotal`, `discount`, `total_amount` nguyên đồng. `discount.amount` = subtotal − total nên cộng trừ luôn khớp."""
    subtotal = money_vnd(sum((l.amount + l.discount_amount for l in order.lines.all()), ZERO))
    total = money_vnd(order.total_amount)
    discount = max(subtotal - total, ZERO)
    return {
        "subtotal": money_str(subtotal),
        "discount": {
            "source": "promo" if discount > ZERO else None,
            "code": None,
            "amount": money_str(discount),
        },
        "total_amount": money_str(total),
    }


def booked_expires_payload(order):
    """Chỉ khi còn `BOOKED` (không rò TTL của đơn đã chốt)."""
    if order.status == SalesOrder.Status.BOOKED:
        return iso_utc(order.booked_expires_at)
    return None


def create_payload(order, *, now):
    return {
        "order_code": order.code,
        "status": order.status,
        **money_block(order),
        "booked_expires_at": booked_expires_payload(order),
        "server_now": iso_utc(now),
        "hold_minutes": settings.SALES_ORDER_TTL_MINUTES,
        "lines": lines_payload(order),
        "lookup_token": make_token(order.code),
    }
