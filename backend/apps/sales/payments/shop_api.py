"""
Shop API công khai (guest) — P1: lập tham số thanh toán cổng SePay cho một đơn.

Không yêu cầu SĐT (khác `ShopOrderLookupView`) vì response KHÔNG chứa thông tin khách (P1-AC6): chỉ mã đơn, tiền, URL,
chữ ký, vốn đã đủ để chuyển hướng khách sang SePay.

Lỗi chuẩn hoá theo 02b §3.5 (Shop lô 3+4): 404 `ORDER_NOT_FOUND`; 400 `CHECKOUT_UNAVAILABLE` với `reason` là mã
`BusinessError` gốc (chỉ để log/QA, FE không hiện cho khách). Thân 200 giữ nguyên.
"""
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.exceptions import BusinessError
from apps.common.throttling import ShopCheckoutThrottle
from apps.sales.models import SalesOrder

from . import checkout

ORDER_NOT_FOUND = {"code": "ORDER_NOT_FOUND", "detail": "Không tìm thấy đơn."}
CHECKOUT_UNAVAILABLE_DETAIL = "Chưa mở được trang thanh toán. Thử lại."


class ShopOrderCheckoutView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ShopCheckoutThrottle]

    def post(self, request, order_code):
        order = SalesOrder.objects.filter(code=order_code).first()
        if order is None:
            return Response(ORDER_NOT_FOUND, status=404)
        try:
            params = checkout.build_checkout_params(order=order)
        except BusinessError as exc:
            return Response(
                {"code": "CHECKOUT_UNAVAILABLE", "detail": CHECKOUT_UNAVAILABLE_DETAIL, "reason": exc.code},
                status=400,
            )
        return Response(params, status=200)
