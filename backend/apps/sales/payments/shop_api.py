"""
Shop API công khai (guest) — P1: lập tham số thanh toán cổng SePay cho một đơn.

Không yêu cầu 4 số cuối SĐT (khác `ShopOrderLookupView`) vì response KHÔNG chứa thông tin
khách (P1-AC6) — chỉ mã đơn/tiền/URL/chữ ký, vốn đã đủ để chuyển hướng khách sang SePay.
"""
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.exceptions import BusinessError
from apps.sales.models import SalesOrder

from . import checkout


class ShopOrderCheckoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, order_code):
        order = SalesOrder.objects.filter(code=order_code).first()
        if order is None:
            return Response({"detail": "Không tìm thấy đơn."}, status=404)
        try:
            params = checkout.build_checkout_params(order=order)
        except BusinessError as exc:
            return Response({"detail": str(exc), "code": exc.code}, status=400)
        return Response(params, status=200)
