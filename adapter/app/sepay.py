"""Transform payload SePay -> body nội bộ cho Django. Không có logic nghiệp vụ
(idempotency, khớp đơn, v.v.) ở đây — tất cả nằm ở Django (sales.confirm_payment),
đúng nguyên tắc "adapter là lớp mỏng" (ecosystem-l1.md mục 3)."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from .schemas import InternalPaymentPayload, SePayIpnPayload, SePayWebhookPayload, parse_sepay_datetime


def parse_transaction_date(raw: str) -> str:
    """
    Chuẩn hoá transactionDate của SePay về ISO 8601 để Django (DRF DateTimeField)
    parse được. Fallback: nếu SePay đổi format sang ISO sẵn thì dùng luôn.
    """
    return parse_sepay_datetime(raw).isoformat()


def extract_order_code(payload: SePayWebhookPayload, fallback_pattern: str) -> str:
    """
    Rút mã đơn hàng (order_code) từ payload SePay.

    Thứ tự ưu tiên:
    1. field `code` — SePay tự nhận diện theo cấu hình tiền tố mã hoá đơn trên
       dashboard (xem docstring app/schemas.py).
    2. fallback: regex `fallback_pattern` (mặc định 1-4 chữ + >=4 số, cấu hình
       qua env ORDER_CODE_REGEX) dò trong `content` rồi `description`.

    Nếu không tìm được gì, trả chuỗi rỗng — KHÔNG raise lỗi ở đây: một giao dịch
    tiền vào không khớp được order_code vẫn là dữ liệu hợp lệ cần forward cho
    Django xử lý như thanh toán "mồ côi" (BR-TT-05, Chủ xử lý thủ công), không
    phải lỗi request để adapter tự chặn.
    """
    if payload.code and payload.code.strip():
        return payload.code.strip().upper()

    compiled = re.compile(fallback_pattern, re.IGNORECASE)
    for text in (payload.content, payload.description or ""):
        match = compiled.search(text or "")
        if match:
            return match.group(0).upper()
    return ""


def is_incoming_transfer(payload: SePayWebhookPayload) -> bool:
    """True nếu là giao dịch tiền VÀO (transferType == "in")."""
    return payload.transfer_type.strip().lower() == "in"


def normalize_bank_txn_id(raw: object) -> str:
    """
    Dạng chuẩn mã giao dịch ngân hàng: bỏ MỌI khoảng trắng, viết hoa. PHẢI giống hệt
    Django `apps.sales.payments.services.normalize_bank_txn_id` (Django chuẩn hoá lại lần
    nữa, đây chỉ để body gửi đi đã sạch).
    """
    if raw is None:
        return ""
    return "".join(str(raw).split()).upper()


def pick_bank_txn_id(payload: SePayWebhookPayload) -> str:
    """
    QA L7 · B12 / BR-TT-03: dùng `referenceCode` (mã FT… ngân hàng in trên sao kê — đúng
    mã Chủ gõ khi xác nhận tay) làm bank_txn_id, để webhook đến muộn trùng với giao dịch
    Chủ đã ghi. Chỉ lùi về `id` nội bộ SePay khi referenceCode trống. `id` SePay vẫn nằm
    trong `raw` (Django lưu raw_payload) để đối soát.
    """
    return normalize_bank_txn_id(payload.reference_code) or str(payload.id)


def to_internal_payload(payload: SePayWebhookPayload, order_code_regex: str) -> InternalPaymentPayload:
    """Map payload SePay -> body nội bộ đúng Contract B."""
    return InternalPaymentPayload(
        bank_txn_id=pick_bank_txn_id(payload),
        order_code=extract_order_code(payload, order_code_regex),
        amount=payload.transfer_amount,
        received_at=parse_transaction_date(payload.transaction_date),
        raw=payload.model_dump(by_alias=True, mode="json"),
    )


# --- IPN Cổng thanh toán SePay (story P2, hồ sơ 2026-09-26-sepay-cong-thanh-toan) --------

VN_TZ = timezone(timedelta(hours=7))

# Q4 (01-analysis.md, vẫn ĐỎ): chưa có payload sandbox thật để đối chiếu 1:1 lúc build.
# Ưu tiên mã tham chiếu ngân hàng (FT…, đúng mã Chủ gõ khi xác nhận tay S11, BR-TT-03) nếu
# IPN có; danh sách tên field ứng viên xếp theo độ ưu tiên. Lùi về id giao dịch của SePay
# khi không field nào khớp. CHỈNH LẠI danh sách này khi có payload sandbox thật (ghi vào
# 03-dev-notes.md).
_IPN_REFERENCE_CODE_KEYS = (
    "reference_code",
    "reference_number",
    "bank_reference_code",
    "bank_transaction_id",
)
_IPN_TRANSACTION_ID_KEYS = ("id", "transaction_id", "transaction_code")

# Mã đơn dạng SO<yymmdd>-<6 ký tự hex> (01-analysis.md §3.2). Thanh toán lại (UC-2, Q5) có
# thể cần hậu tố lần thử (vd "-2") nếu SePay không nhận lại đúng order_invoice_number cũ —
# bóc hậu tố đó trước khi khớp đơn. GIẢ ĐỊNH: định dạng hậu tố do BE (P1) chọn; kiểm lại khi
# P1 xong nếu khác "-<số>".
_ORDER_CODE_WITH_RETRY_SUFFIX = re.compile(r"^(SO\d{6}-[0-9A-Za-z]{6})(?:-\d+)?$")

# Giao dịch cổng thanh toán (VietQR duy nhất ở V1) — luôn VND.
IPN_CONFIRM_CURRENCY = "VND"
IPN_CONFIRM_ORDER_STATUS = "CAPTURED"

NOTIFICATION_ORDER_PAID = "ORDER_PAID"
NOTIFICATION_TRANSACTION_VOID = "TRANSACTION_VOID"


class IpnMalformedError(ValueError):
    """Payload IPN hỏng vĩnh viễn (thiếu mã đơn/số tiền/mã giao dịch, E9) — route trả 400,
    KHÔNG 500, để không gây vòng SePay gửi lại vô hạn."""


def strip_order_retry_suffix(order_invoice_number: str) -> str:
    """Bóc hậu tố lần thử (Q5) khỏi order_invoice_number để khớp đúng mã đơn gốc.
    Không khớp định dạng đã biết -> giữ nguyên chuỗi (khớp thất bại là ca nghiệp vụ hợp lệ,
    Django tự xử lý UNMATCHED — không phải lỗi request của adapter)."""
    value = (order_invoice_number or "").strip().upper()
    match = _ORDER_CODE_WITH_RETRY_SUFFIX.match(value)
    return match.group(1) if match else value


def pick_ipn_transaction_reference(transaction: dict[str, Any]) -> str:
    """Chọn mã giao dịch duy nhất từ sub-object `transaction` của IPN (BR-TT-03/Q4):
    ưu tiên mã tham chiếu ngân hàng (FT…) nếu có, lùi về id giao dịch của SePay."""
    for key in _IPN_REFERENCE_CODE_KEYS:
        raw = transaction.get(key)
        normalized = normalize_bank_txn_id(raw)
        if normalized:
            return normalized
    for key in _IPN_TRANSACTION_ID_KEYS:
        raw = transaction.get(key)
        normalized = normalize_bank_txn_id(raw)
        if normalized:
            return normalized
    return ""


# Tên field ứng viên chứa thời điểm giao dịch trong sub-object `transaction` — chưa có
# payload sandbox thật để chốt (Q4). Không tìm được field nào parse được -> dùng thời điểm
# adapter nhận IPN (giờ VN) làm received_at, KHÔNG coi là payload hỏng (chỉ 3 field mã đơn/
# số tiền/mã giao dịch mới bắt buộc, theo P2-AC5).
_IPN_TIMESTAMP_KEYS = ("paid_at", "captured_at", "transaction_time", "transaction_date", "created_at")


def _extract_ipn_received_at(transaction: dict[str, Any]) -> str:
    for key in _IPN_TIMESTAMP_KEYS:
        raw = transaction.get(key)
        if not raw:
            continue
        try:
            return parse_sepay_datetime(str(raw)).isoformat()
        except (TypeError, ValueError):
            continue
    return datetime.now(VN_TZ).isoformat()


def is_ipn_order_paid(payload: SePayIpnPayload) -> bool:
    return payload.notification_type == NOTIFICATION_ORDER_PAID


def is_ipn_transaction_void(payload: SePayIpnPayload) -> bool:
    return payload.notification_type == NOTIFICATION_TRANSACTION_VOID


def is_ipn_status_confirmable(payload: SePayIpnPayload) -> bool:
    """P2-AC6/Q9: chỉ xác nhận khi order.status=CAPTURED và currency=VND."""
    order = payload.order
    status_ok = (order.status or "").strip().upper() == IPN_CONFIRM_ORDER_STATUS
    currency_ok = (order.currency or "").strip().upper() == IPN_CONFIRM_CURRENCY
    return status_ok and currency_ok


def to_internal_payload_from_ipn(payload: SePayIpnPayload) -> InternalPaymentPayload:
    """Map IPN `ORDER_PAID`+CAPTURED+VND -> body nội bộ (P2-AC1). Raise `IpnMalformedError`
    (E9) khi thiếu mã đơn/số tiền/mã giao dịch — payload hỏng vĩnh viễn, không phải ca
    nghiệp vụ (khớp thất bại vẫn để Django xử lý qua order_code rỗng ở webhook cũ, nhưng ở
    đây thiếu order_invoice_number nghĩa là SePay gửi thiếu field bắt buộc)."""
    order_invoice_number = (payload.order.order_invoice_number or "").strip()
    if not order_invoice_number:
        raise IpnMalformedError("Thiếu order.order_invoice_number.")
    if payload.order.amount is None:
        raise IpnMalformedError("Thiếu order.amount.")

    bank_txn_id = pick_ipn_transaction_reference(payload.transaction)
    if not bank_txn_id:
        raise IpnMalformedError("Thiếu mã giao dịch (transaction.id/reference_code).")

    return InternalPaymentPayload(
        bank_txn_id=bank_txn_id,
        order_code=strip_order_retry_suffix(order_invoice_number),
        amount=payload.order.amount,
        received_at=_extract_ipn_received_at(payload.transaction),
        raw=payload.model_dump(mode="json"),
    )
