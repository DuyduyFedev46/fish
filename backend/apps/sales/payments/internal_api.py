"""
API nội bộ cho adapter (FastAPI) gọi vào — KHÔNG mở ra ngoài.

Xác thực bằng service token riêng (X-Internal-Token), tách khỏi auth của Next.js.
Bên thứ 3 (SePay) không bao giờ nối thẳng — luôn qua adapter rồi vào đây (ecosystem-l1 §3).
"""
import hmac
from django.conf import settings
from django.utils.dateparse import parse_datetime
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.exceptions import BusinessError
from apps.sales.models import PaymentTransaction, SalesOrder
from apps.sales.utils import money_str

from . import services

WEBHOOK_INVALID_INPUT = "WEBHOOK_INVALID_INPUT"
BANK_TXN_ID_MAX_LENGTH = services.BANK_TXN_ID_MAX_LENGTH  # 100


def _invalid(detail):
    return Response({"detail": detail, "code": WEBHOOK_INVALID_INPUT}, status=400)


def _token_ok(token):
    """R3 (review): so token hằng thời gian; token chưa cấu hình → luôn từ chối."""
    expected = settings.INTERNAL_SERVICE_TOKEN or ""
    if not expected:
        return False
    return hmac.compare_digest(str(token).encode("utf-8"), expected.encode("utf-8"))


def _existing_response(payment):
    """R5 (review): giao dịch đã ghi trước đó → trả đúng kết quả thực tế (idempotent)."""
    order = payment.sales_order
    return Response(_result_body(payment, order.status if order is not None else None))


def _result_body(payment, order_status):
    """Kết quả gửi adapter; `overpaid_amount` chỉ có khi phần thừa đã tách vào hàng chờ (L8)."""
    body = {
        "matched": payment.match_status == PaymentTransaction.MatchStatus.MATCHED,
        "order_status": order_status,
        "match_status": payment.match_status,
    }
    extra = services.overpaid_amount(payment)
    if extra is not None:
        body["overpaid_amount"] = money_str(extra)
    return body


def _parse_payment_body(d):
    """
    Kiểm + chuẩn hoá body {bank_txn_id, order_code, amount, received_at} — DÙNG CHUNG cho
    webhook biến động số dư cũ và IPN Cổng SePay mới (P3), vì cả hai gọi cùng lõi
    `_record_payment`/`confirm_payment` (BR-TT-02/03). Trả
    (bank_txn_id, order_code, amount, received_at, error_response); error_response
    None nghĩa là hợp lệ.
    """
    bank_txn_id = services.normalize_bank_txn_id(d.get("bank_txn_id"))  # B12
    order_code = str(d.get("order_code") or "").strip()
    if not bank_txn_id:
        return None, None, None, None, _invalid("Thiếu bank_txn_id.")
    if len(bank_txn_id) > BANK_TXN_ID_MAX_LENGTH:
        return None, None, None, None, _invalid(f"bank_txn_id dài quá {BANK_TXN_ID_MAX_LENGTH} ký tự.")
    try:
        amount = services.validate_amount(d.get("amount"))  # R1 (review) + B13
    except ValueError as exc:
        return None, None, None, None, _invalid(f"Số tiền (amount) không hợp lệ — {exc}")
    # QA lần 2 · N3: validate trước khi ghi — thiếu/sai received_at trước đây lọt xuống DB
    # (NOT NULL) thành 500. Adapter luôn gửi ISO 8601 nên hành vi khi đủ trường không đổi.
    try:
        received_at = parse_datetime(str(d.get("received_at") or ""))
    except ValueError:
        received_at = None
    if received_at is None:
        return None, None, None, None, _invalid("Thiếu hoặc sai received_at (ISO 8601).")
    return bank_txn_id, order_code, amount, received_at, None


def _handle_payment_ipn(request, *, source):
    """Lõi chung webhook ngân hàng cũ (WEBHOOK) và IPN Cổng SePay mới (GATEWAY, P3)."""
    if not _token_ok(request.headers.get("X-Internal-Token", "")):
        return Response({"detail": "Sai service token."}, status=401)

    d = request.data if isinstance(request.data, dict) else {}
    bank_txn_id, order_code, amount, received_at, error = _parse_payment_body(d)
    if error is not None:
        return error

    order = SalesOrder.objects.filter(code=order_code).first() if order_code else None
    if order is None:
        # BR-TT-03: giao dịch đã ghi (vd lần đầu khớp đơn, lần gửi lại thiếu order_code)
        # → trả đúng kết quả đã ghi, không ghi thêm.
        existing = (PaymentTransaction.objects.select_related("sales_order")
                    .filter(bank_txn_id=bank_txn_id).first())
        if existing is not None:
            return _existing_response(existing)
        # Không khớp đơn nào -> hàng chờ Chủ (BR-TT-05 tinh thần), idempotent theo txn.
        payment, _ = PaymentTransaction.objects.get_or_create(
            bank_txn_id=bank_txn_id,
            defaults={
                "sales_order": None,
                "amount": amount,
                "match_status": PaymentTransaction.MatchStatus.UNMATCHED,
                "resolution_status": services.initial_resolution_status(
                    PaymentTransaction.MatchStatus.UNMATCHED
                ),  # BR-TT-09: vào hàng chờ
                "source": source,
                "environment": services.environment_for_source(source),  # BR-TT-14
                "raw_payload": d.get("raw") or {},
                "received_at": received_at,
            },
        )
        return Response({"matched": False, "order_status": None})

    try:
        payment = services.confirm_payment(
            order=order, bank_txn_id=bank_txn_id, amount=amount,
            received_at=received_at, source=source,
            raw_payload=d.get("raw") or {},
        )
    except BusinessError as exc:
        return Response({"detail": str(exc), "code": exc.code}, status=400)

    order.refresh_from_db()
    return Response(_result_body(payment, order.status))


class SepayWebhookInternalView(APIView):
    """
    Webhook BIẾN ĐỘNG SỐ DƯ cũ (giữ code, KHÔNG khai trên SePay ở V1 — quyết định Duy
    2026-09-26). Nguồn ghi vẫn là `Source.WEBHOOK`.
    """

    permission_classes = [AllowAny]  # tự kiểm token nội bộ bên dưới

    def post(self, request):
        return _handle_payment_ipn(request, source=PaymentTransaction.Source.WEBHOOK)


class SepayGatewayIpnInternalView(APIView):
    """
    P3 (BR-TT-02/03/14): IPN Cổng thanh toán SePay (hosted checkout, adapter route
    `POST /ipn/sepay`) — khác hẳn webhook biến động số dư cũ. Adapter chuẩn hoá payload
    IPN (`ORDER_PAID`/`order.status=CAPTURED`/`currency=VND`, đã lọc ở P2-AC6/Q9 TRƯỚC khi
    gọi vào đây) rồi POST cùng contract {bank_txn_id, order_code, amount, received_at, raw}
    (Contract B, không đổi). Nguồn ghi là `Source.GATEWAY`, môi trường lấy từ
    `settings.SEPAY_ENV` (BR-TT-14, `environment_for_source`).
    """

    permission_classes = [AllowAny]  # tự kiểm token nội bộ bên dưới

    def post(self, request):
        return _handle_payment_ipn(request, source=PaymentTransaction.Source.GATEWAY)
