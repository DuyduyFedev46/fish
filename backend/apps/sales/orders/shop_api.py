"""
Shop API công khai — đặt hàng & tra cứu đơn (guest checkout, 7.1).

- Đặt hàng: gọi orders.services.create_order (Hệ thống tạo, BR-PQ-11).
- Tra đơn: mã đơn + 4 số cuối SĐT (không cần đăng nhập).
- Lập tham số thanh toán cổng SePay: `apps.sales.payments.shop_api.ShopOrderCheckoutView`
  (P1, BR-TT-01/13/14/17) — KHÔNG còn mã VietQR giả (BR-TT-01, quyết định Duy 2026-09-26).
KHÔNG có phí giao hàng (BR-BH-10).
"""
import re
from decimal import Decimal, InvalidOperation

from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.exceptions import BusinessError
from apps.common.throttling import (
    ShopLookupIpThrottle,
    ShopLookupOrderThrottle,
    ShopOrderCreateThrottle,
)
from apps.sales.models import SalesOrder

from . import services

LOOKUP_NOT_FOUND = "Không tìm thấy đơn với mã và số điện thoại này."
LOOKUP_BAD_LAST4 = "Vui lòng nhập đúng 4 số cuối số điện thoại."
_LAST4 = re.compile(r"\d{4}")


class ShopOrderCreateView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ShopOrderCreateThrottle]

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
    throttle_classes = [ShopLookupIpThrottle, ShopLookupOrderThrottle]

    def get(self, request, order_code):
        phone_last4 = request.query_params.get("phone_last4", "")
        if not _LAST4.fullmatch(phone_last4):
            return Response({"detail": LOOKUP_BAD_LAST4}, status=400)

        order = SalesOrder.objects.select_related("customer").filter(code=order_code).first()
        digits = re.sub(r"\D", "", order.phone) if order and order.phone else ""
        if order is None or len(digits) < 4 or digits[-4:] != phone_last4:
            return Response({"detail": LOOKUP_NOT_FOUND}, status=404)

        delivery = None
        status_label = order.get_status_display()
        invoice = getattr(order, "invoice", None)
        if invoice is not None:
            dn = invoice.delivery_notes.first()
            if dn is not None:
                deliv_label = dn.get_status_display()
                if dn.status == "CONFIRMING":
                    deliv_label = "Chờ vựa gọi xác nhận"
                    if order.status == SalesOrder.Status.PROCESSING:
                        status_label = "Đã thanh toán – chờ vựa gọi xác nhận"
                elif dn.status == "CANCELLED" and order.status == SalesOrder.Status.CANCELLED:
                    deliv_label = "Đã huỷ theo đơn"
                delivery = {"status": dn.status, "status_label": deliv_label}

        booked_expires_at = None
        if order.status == SalesOrder.Status.BOOKED and order.booked_expires_at is not None:
            # Giờ VN (BR-BH-03): FE hiện đồng hồ đếm ngược, không tự suy đoán từ UTC.
            booked_expires_at = timezone.localtime(order.booked_expires_at).isoformat()

        from .customer_notices import build_cancel_notice
        cancel_notice = build_cancel_notice(order)

        return Response(
            {
                "order_code": order.code,
                "status": order.status,
                "status_label": status_label,
                "total_amount": str(order.total_amount),
                "lines": [
                    {
                        "item_code": l.item.code,
                        "name": l.item.name,
                        "qty": str(l.qty),
                        "amount": str(l.amount),
                    }
                    for l in order.lines.select_related("item")
                ],
                "delivery": delivery,
                "booked_expires_at": booked_expires_at,
                "cancel_notice": cancel_notice,
            }
        )
