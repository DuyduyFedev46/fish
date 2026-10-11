"""
Dict JSON của mã giảm giá cho ERP (02b §3.9). Dựng tường minh, KHÔNG `fields="__all__"`.
Không có tên, SĐT, địa chỉ khách, giá vốn hay lãi (bất biến 1 và 9).
"""
from apps.common.formatting import iso_utc
from apps.sales.utils import money_str

from . import services


def voucher_payload(voucher, *, now) -> dict:
    """`voucher` đã qua `services.with_counts` (có `used_count`, `held_count`)."""
    committed = voucher.used_count + voucher.held_count
    return {
        "id": voucher.pk,
        "code": voucher.code,
        "name": voucher.name,
        "kind": voucher.kind,
        "value": money_str(voucher.value),
        "max_discount": money_str(voucher.max_discount),
        "min_order_amount": money_str(voucher.min_order_amount),
        "starts_at": iso_utc(voucher.starts_at),
        "ends_at": iso_utc(voucher.ends_at),
        "total_uses": voucher.total_uses,
        "used_count": voucher.used_count,
        "held_count": voucher.held_count,
        "status": services.voucher_status(voucher, now=now, committed=committed),
        "is_active": voucher.is_active,
        "disabled_reason": voucher.disabled_reason,
        "disabled_note": voucher.disabled_note,
        "customer_terms": voucher.customer_terms,
        "created_at": iso_utc(voucher.created_at),
    }


def redemption_payload(redemption) -> dict:
    """Đúng 4 khoá (SHOP-3b-01 AC10): không tên, SĐT, địa chỉ, giá vốn."""
    at = {
        redemption.State.USED: redemption.used_at,
        redemption.State.RELEASED: redemption.released_at,
    }.get(redemption.state) or redemption.held_at
    return {
        "order_code": redemption.order.code,
        "discount_amount": money_str(redemption.discount_amount),
        "at": iso_utc(at),
        "state": redemption.state.lower(),
    }
