"""
Shop API công khai — đặt hàng & tra cứu đơn (guest checkout, 7.1).

- Đặt hàng: gọi orders.services.create_order (Hệ thống tạo, BR-PQ-11).
- Tra đơn: mã đơn + 4 số cuối SĐT (không cần đăng nhập).
- Lập tham số thanh toán cổng SePay: `apps.sales.payments.shop_api.ShopOrderCheckoutView`
  (P1, BR-TT-01/13/14/17) — KHÔNG còn mã VietQR giả (BR-TT-01, quyết định Duy 2026-09-26).
KHÔNG có phí giao hàng (BR-BH-10).
"""
from decimal import Decimal, InvalidOperation

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.exceptions import BusinessError
from apps.sales.models import SalesOrder

from . import services


class ShopOrderCreateView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        d = request.data or {}
        customer = d.get("customer") or {}
        items = d.get("items") or []
        try:
            lines = [
                {"item_code": it["item_code"], "qty": Decimal(str(it["qty"]))}
                for it in items
            ]
        except (KeyError, TypeError, InvalidOperation):
            return Response({"detail": "Dữ liệu giỏ hàng không hợp lệ."}, status=400)

        try:
            order = services.create_order(
                customer_phone=(customer.get("phone") or "").strip(),
                customer_name=(customer.get("name") or "").strip(),
                delivery_address=(d.get("delivery_address") or "").strip(),
                phone=(d.get("phone") or customer.get("phone") or "").strip(),
                lines=lines,
            )
        except BusinessError as exc:
            return Response({"detail": str(exc), "code": exc.code}, status=400)

        return Response(
            {
                "order_code": order.code,
                "total_amount": str(order.total_amount),
                "booked_expires_at": order.booked_expires_at,
            },
            status=201,
        )


class ShopOrderLookupView(APIView):
    """Tra đơn bằng mã đơn + 4 số cuối SĐT (7.1)."""

    permission_classes = [AllowAny]

    def get(self, request, order_code):
        phone_last4 = request.query_params.get("phone_last4", "")
        try:
            order = SalesOrder.objects.select_related("customer").get(code=order_code)
        except SalesOrder.DoesNotExist:
            return Response({"detail": "Không tìm thấy đơn."}, status=404)
        if not phone_last4 or not order.phone.endswith(phone_last4):
            return Response({"detail": "Sai mã đơn hoặc số điện thoại."}, status=404)

        delivery = None
        invoice = getattr(order, "invoice", None)
        if invoice is not None:
            dn = invoice.delivery_notes.first()
            if dn is not None:
                delivery = {"status": dn.status, "status_label": dn.get_status_display()}

        return Response(
            {
                "order_code": order.code,
                "status": order.status,
                "status_label": order.get_status_display(),
                "total_amount": str(order.total_amount),
                "lines": [
                    {"item_code": l.item.code, "qty": str(l.qty), "amount": str(l.amount)}
                    for l in order.lines.select_related("item")
                ],
                "delivery": delivery,
            }
        )
