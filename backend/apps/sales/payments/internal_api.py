"""
API nội bộ cho adapter (FastAPI) gọi vào — KHÔNG mở ra ngoài.

Xác thực bằng service token riêng (X-Internal-Token), tách khỏi auth của Next.js.
Bên thứ 3 (SePay) không bao giờ nối thẳng — luôn qua adapter rồi vào đây (ecosystem-l1 §3).
"""
import hmac
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.utils.dateparse import parse_datetime
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.exceptions import BusinessError
from apps.sales.models import PaymentTransaction, SalesOrder

from . import services

WEBHOOK_INVALID_INPUT = "WEBHOOK_INVALID_INPUT"
BANK_TXN_ID_MAX_LENGTH = PaymentTransaction._meta.get_field("bank_txn_id").max_length  # 100


def _invalid(detail):
    return Response({"detail": detail, "code": WEBHOOK_INVALID_INPUT}, status=400)


def _token_ok(token):
    """R3 (review): so token hằng thời gian; token chưa cấu hình → luôn từ chối."""
    expected = settings.INTERNAL_SERVICE_TOKEN or ""
    if not expected:
        return False
    return hmac.compare_digest(str(token).encode("utf-8"), expected.encode("utf-8"))


def _parse_amount(raw):
    """R1 (review): số tiền phải là số hữu hạn > 0 — chặn 'NaN'/'Infinity'/âm/0/kiểu lạ."""
    if raw is None or isinstance(raw, (bool, list, dict)):
        return None
    try:
        amount = Decimal(str(raw).strip())
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not amount.is_finite() or amount <= 0:
        return None
    return amount


def _existing_response(payment):
    """R5 (review): giao dịch đã ghi trước đó → trả đúng kết quả thực tế (idempotent)."""
    order = payment.sales_order
    return Response(
        {
            "matched": payment.match_status == PaymentTransaction.MatchStatus.MATCHED,
            "order_status": order.status if order is not None else None,
            "match_status": payment.match_status,
        }
    )


class SepayWebhookInternalView(APIView):
    permission_classes = [AllowAny]  # tự kiểm token nội bộ bên dưới

    def post(self, request):
        if not _token_ok(request.headers.get("X-Internal-Token", "")):
            return Response({"detail": "Sai service token."}, status=401)

        d = request.data if isinstance(request.data, dict) else {}
        bank_txn_id = str(d.get("bank_txn_id") or "").strip()
        order_code = str(d.get("order_code") or "").strip()
        if not bank_txn_id:
            return _invalid("Thiếu bank_txn_id.")
        if len(bank_txn_id) > BANK_TXN_ID_MAX_LENGTH:
            return _invalid(f"bank_txn_id dài quá {BANK_TXN_ID_MAX_LENGTH} ký tự.")
        amount = _parse_amount(d.get("amount"))
        if amount is None:
            return _invalid("Số tiền (amount) không hợp lệ — phải là số hữu hạn lớn hơn 0.")
        # QA lần 2 · N3: validate trước khi ghi — thiếu/sai received_at trước đây lọt xuống DB
        # (NOT NULL) thành 500. Adapter luôn gửi ISO 8601 nên hành vi khi đủ trường không đổi.
        try:
            received_at = parse_datetime(str(d.get("received_at") or ""))
        except ValueError:
            received_at = None
        if received_at is None:
            return _invalid("Thiếu hoặc sai received_at (ISO 8601).")

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
                    "source": PaymentTransaction.Source.WEBHOOK,
                    "raw_payload": d.get("raw") or {},
                    "received_at": received_at,
                },
            )
            return Response({"matched": False, "order_status": None})

        try:
            payment = services.confirm_payment(
                order=order, bank_txn_id=bank_txn_id, amount=amount,
                received_at=received_at, source=PaymentTransaction.Source.WEBHOOK,
                raw_payload=d.get("raw") or {},
            )
        except BusinessError as exc:
            return Response({"detail": str(exc), "code": exc.code}, status=400)

        order.refresh_from_db()
        return Response(
            {
                "matched": payment.match_status == PaymentTransaction.MatchStatus.MATCHED,
                "order_status": order.status,
                "match_status": payment.match_status,
            }
        )
