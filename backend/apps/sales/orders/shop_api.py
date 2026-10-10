"""
Shop API công khai — đặt hàng & tra cứu đơn (guest checkout). Contract: 02b §3.3, §3.4.

- Đặt hàng: kiểm theo đúng thứ tự §3.3 (SHOP_CLOSED, VALIDATION, đơn cũ, INVALID_QTY, POLICY_CHANGED, OUT_OF_STOCK), rồi
  `services.place_order` (Hệ thống tạo, BR-PQ-11; chống trùng `client_request_id`, BR-BH-27). Trả dòng món, `lookup_token`.
- Tra đơn: POST mã đơn + SĐT đầy đủ hoặc mã tra đơn (BR-BH-25). GET 4 số cuối đã GỠ. Không trả người nhận (decisions 10/10).
- Lập tham số thanh toán cổng SePay: `apps.sales.payments.shop_api.ShopOrderCheckoutView`.
KHÔNG có phí giao hàng (BR-BH-10). Không log `request.data` (bất biến 9): chỉ mã đơn và SĐT đã che.
"""
import hmac
import logging
import re
import uuid
from decimal import Decimal, InvalidOperation

from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.api import NoStoreMixin
from apps.common.formatting import iso_utc
from apps.common.pii import mask_phone, normalize_phone
from apps.common.throttling import (
    body_dict,
    ShopLookupIpThrottle,
    ShopLookupOrderThrottle,
    ShopLookupTokenThrottle,
    ShopOrderCreateThrottle,
)
from apps.sales.models import SalesOrder

from . import consent, lookup_token, services, shop_payload, shop_state
from .customer_notices import build_cancel_notice
from .shop_errors import validation_error

logger = logging.getLogger(__name__)

ORDER_NOT_FOUND = {
    "code": "ORDER_NOT_FOUND",
    "detail": "Không tìm thấy đơn khớp mã và số điện thoại.",
}
TOKEN_EXPIRED = {
    "code": "TOKEN_EXPIRED",
    "detail": "Phiên xem đơn đã hết hạn. Nhập số điện thoại để xem lại.",
}
PHONE_RULE = "Số điện thoại cần 10 chữ số, bắt đầu bằng 0"
_PHONE_RE = re.compile(r"0\d{9}")
NAME_MAX = 100
ADDRESS_MAX = 500


_body = body_dict


def _text(value) -> str:
    return value.strip() if isinstance(value, str) else ""


# --- Tạo đơn ------------------------------------------------------------------------------------

def _parse_lines(items, fields: dict):
    """items -> [{item_code, qty: Decimal}]; ghi lỗi vào `fields["items"]` (02b §3.3 #2), không ném."""
    if not isinstance(items, list) or not items:
        fields["items"] = "Giỏ hàng đang trống."
        return []
    if len(items) > settings.SHOP_MAX_ORDER_LINES:
        fields["items"] = f"Mỗi đơn tối đa {settings.SHOP_MAX_ORDER_LINES} món."
        return []
    lines, seen = [], set()
    try:
        for it in items:
            code = _text(it["item_code"])
            qty = Decimal(str(it["qty"]).strip())
            if not code or not qty.is_finite():
                raise InvalidOperation
            if code in seen:
                fields["items"] = "Mỗi món chỉ được xuất hiện một lần trong đơn."
                return []
            seen.add(code)
            lines.append({"item_code": code, "qty": qty})
    except (KeyError, TypeError, InvalidOperation, AttributeError):
        fields["items"] = "Số lượng chưa hợp lệ."
        return []
    return lines


def _parse_create_body(d: dict) -> dict:
    """Bước 2 §3.3: gom MỌI lỗi theo ô rồi ném một `VALIDATION`. Khoá `phone` cấp ngoài bị bỏ (chỉ `customer.phone`)."""
    fields: dict = {}

    request_id = None
    raw_id = d.get("client_request_id")
    if raw_id not in (None, ""):
        try:
            request_id = uuid.UUID(raw_id) if isinstance(raw_id, str) else None
        except ValueError:
            request_id = None
        if request_id is None:
            fields["client_request_id"] = "Mã yêu cầu không hợp lệ."

    customer = d.get("customer") if isinstance(d.get("customer"), dict) else {}
    name = _text(customer.get("name"))
    if not name or len(name) > NAME_MAX:
        fields["name"] = f"Nhập họ tên (tối đa {NAME_MAX} ký tự)."

    phone = normalize_phone(customer.get("phone") if isinstance(customer.get("phone"), str) else "")
    if not _PHONE_RE.fullmatch(phone):
        fields["phone"] = PHONE_RULE

    address = _text(d.get("delivery_address"))
    if not address or len(address) > ADDRESS_MAX:
        fields["delivery_address"] = f"Nhập địa chỉ giao hàng (tối đa {ADDRESS_MAX} ký tự)."

    lines = _parse_lines(d.get("items"), fields)

    consent_payload = d.get("privacy_consent")
    message = consent.consent_field_error(consent_payload)
    if message:
        fields["consent"] = message

    if fields:
        raise validation_error(**fields)
    return {
        "client_request_id": request_id,
        "name": name,
        "phone": phone,
        "address": address,
        "lines": lines,
        "privacy_consent": consent_payload,
    }


class ShopOrderCreateView(NoStoreMixin, APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ShopOrderCreateThrottle]

    def post(self, request):
        d = _body(request)
        consent.ensure_shop_open()  # 1. SHOP_CLOSED
        parsed = _parse_create_body(d)  # 2. VALIDATION (không log dữ liệu khách, SHOP-2-02 AC6)

        order, created = services.place_order(
            client_request_id=parsed["client_request_id"],
            customer_phone=parsed["phone"],
            customer_name=parsed["name"],
            delivery_address=parsed["address"],
            phone=parsed["phone"],
            lines=parsed["lines"],
            privacy_consent=parsed["privacy_consent"],
        )
        logger.info("shop order %s created=%s", order.code, created)
        body = shop_payload.create_payload(order, now=services._now())
        return Response(body, status=201 if created else 200)


# --- Tra đơn ------------------------------------------------------------------------------------

class ShopOrderLookupView(NoStoreMixin, APIView):
    """
    `POST /api/shop/orders/lookup/` (BR-BH-25, BR-BH-26). Mọi ca sai (mã, SĐT, token của đơn khác, token hỏng) trả CÙNG
    404; luôn chạy cùng một truy vấn đơn rồi so SĐT bằng `compare_digest` nên thời gian không lộ ô nào sai.
    """

    permission_classes = [AllowAny]

    def get_throttles(self):
        if _text(body_dict(self.request).get("token")):
            return [ShopLookupTokenThrottle()]
        return [ShopLookupIpThrottle(), ShopLookupOrderThrottle()]

    def post(self, request):
        d = _body(request)
        code = _text(d.get("order_code")).upper()
        phone_raw = d.get("phone") if isinstance(d.get("phone"), str) else ""
        token = _text(d.get("token"))

        fields = {}
        if not code:
            fields["order_code"] = "Nhập mã đơn hàng."
        if not token and not phone_raw.strip():
            fields["phone"] = "Nhập số điện thoại đã đặt hàng."
        if fields:
            raise validation_error(**fields)

        order = (
            SalesOrder.objects.select_related("invoice").filter(code=code).first()
        )

        if token:
            try:
                lookup_token.read_token(token, code)
                authorized = order is not None
            except lookup_token.TokenExpired:
                return Response(TOKEN_EXPIRED, status=401)
            except lookup_token.TokenInvalid:
                authorized = False
        else:
            given = normalize_phone(phone_raw).encode()
            actual = normalize_phone(order.phone if order else "").encode()
            same = hmac.compare_digest(given, actual)
            authorized = bool(order is not None and actual and same)

        if not authorized:
            logger.info("shop lookup miss code=%s phone=%s", code, mask_phone(phone_raw) if phone_raw else "-")
            return Response(ORDER_NOT_FOUND, status=404)

        logger.info("shop lookup ok code=%s", code)
        return Response(_lookup_payload(order))


def _lookup_payload(order: SalesOrder) -> dict:
    now = services._now()
    note = shop_state.latest_delivery_note(order)
    has_payment = order.status == SalesOrder.Status.AUTO_CANCELLED and shop_state.has_payment_transaction(order)
    state = shop_state.order_state(order, now=now, note=note, has_payment=has_payment)
    invoice = getattr(order, "invoice", None)
    delivered_at = note.completed_at if note is not None and note.status == "COMPLETED" else None

    return {
        "order_code": order.code,
        "status": order.status,
        "state": state,
        "status_label": shop_state.state_label(state, note),
        "placed_at": iso_utc(order.created_at),
        "paid_at": iso_utc(invoice.issued_at) if invoice is not None else None,
        "delivered_at": iso_utc(delivered_at),
        "booked_expires_at": shop_payload.booked_expires_payload(order),
        "server_now": iso_utc(now),
        "hold_minutes": settings.SALES_ORDER_TTL_MINUTES,
        "payment_pending_minutes": settings.SHOP_PAYMENT_PENDING_MINUTES,
        "delivery": shop_state.delivery_block(note),
        "lines": shop_payload.lines_payload(order),
        **shop_payload.money_block(order),
        "cancel_notice": build_cancel_notice(order, note=note),
        "late_payment": has_payment,
        "lookup_token": lookup_token.make_token(order.code),
    }
