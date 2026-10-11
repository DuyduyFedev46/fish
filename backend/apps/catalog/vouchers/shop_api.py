"""
Shop API công khai — kiểm mã giảm giá với giỏ hiện tại (SHOP-3b-03, BR-DM-24, 02b §3.8).

Dict dựng tường minh. KHÔNG trả: số lượt còn lại hay ai đã dùng, danh sách mã khác, dữ liệu đơn khác, giá vốn, số kg tồn,
tên/SĐT/địa chỉ (bất biến 1 và 9). Throttle `shop_voucher_check` theo IP. Tính giảm bằng `evaluate_voucher`, cùng hàm với
tạo đơn. Không log thân request.
"""
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.api import NoStoreMixin
from apps.common.formatting import iso_utc
from apps.common.throttling import ShopVoucherCheckThrottle, body_dict
from apps.sales.orders import services as order_services
from apps.sales.orders.shop_api import parse_lines
from apps.sales.orders.shop_errors import validation_error
from apps.sales.utils import ZERO, money_str, money_vnd

from . import services


def _terms(voucher) -> dict:
    return {
        "kind": voucher.kind,
        "value": money_str(voucher.value),
        "max_discount": money_str(voucher.max_discount) if voucher.kind == voucher.Kind.PERCENT else None,
        "min_order_amount": money_str(voucher.min_order_amount),
        "starts_at": iso_utc(voucher.starts_at),
        "ends_at": iso_utc(voucher.ends_at),
        "customer_terms": voucher.customer_terms,
    }


class ShopVoucherCheckView(NoStoreMixin, APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ShopVoucherCheckThrottle]

    def post(self, request):
        data = body_dict(request)
        fields: dict = {}
        lines = parse_lines(data.get("items"), fields)
        if fields:
            raise validation_error(**fields)
        raw_code = data.get("code")
        code = services.normalize_code(raw_code) if isinstance(raw_code, str) else ""

        quote = order_services.quote_cart(lines)  # INVALID_QTY / VALIDATION `items`
        subtotal = money_vnd(quote.subtotal)
        auto_total_after = money_vnd(quote.subtotal - quote.auto_discount)
        auto_amount = subtotal - auto_total_after

        voucher, result = (None, None)
        if code:
            voucher, result = order_services.check_voucher(code, quote, now=timezone.now())

        if result is not None and result.valid:
            applied = {"source": "voucher", "amount": money_str(result.discount)}
            total_after = money_vnd(quote.subtotal - result.discount)
        elif auto_amount > ZERO:
            applied = {"source": "promo", "amount": money_str(auto_amount)}
            total_after = auto_total_after
        else:
            applied = {"source": None, "amount": "0"}
            total_after = subtotal

        return Response({
            "code": code or None,
            "valid": None if result is None else result.valid,
            "reason_code": None if result is None else result.reason_code,
            "subtotal": money_str(subtotal),
            "auto_discount_amount": money_str(auto_amount),
            "discount_amount": money_str(result.discount) if result is not None and result.valid else "0",
            "missing_amount": (
                money_str(result.missing_amount) if result is not None and result.missing_amount is not None else None
            ),
            "applied": applied,
            "total_after": money_str(total_after),
            "terms": _terms(voucher) if result is not None and result.terms_visible and voucher is not None else None,
        })
