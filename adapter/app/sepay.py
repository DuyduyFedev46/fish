"""Transform payload SePay -> body nội bộ cho Django. Không có logic nghiệp vụ
(idempotency, khớp đơn, v.v.) ở đây — tất cả nằm ở Django (sales.confirm_payment),
đúng nguyên tắc "adapter là lớp mỏng" (ecosystem-l1.md mục 3)."""

from __future__ import annotations

import re
from datetime import datetime

from .schemas import InternalPaymentPayload, SePayWebhookPayload

# SePay tài liệu ví dụ dùng format "YYYY-MM-DD HH:MM:SS" (giờ VN, không có timezone).
_SEPAY_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def parse_transaction_date(raw: str) -> str:
    """
    Chuẩn hoá transactionDate của SePay về ISO 8601 để Django (DRF DateTimeField)
    parse được. Fallback: nếu SePay đổi format sang ISO sẵn thì dùng luôn.
    """
    try:
        dt = datetime.strptime(raw, _SEPAY_DATE_FORMAT)
    except ValueError:
        dt = datetime.fromisoformat(raw)
    return dt.isoformat()


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


def to_internal_payload(payload: SePayWebhookPayload, order_code_regex: str) -> InternalPaymentPayload:
    """Map payload SePay -> body nội bộ đúng Contract B."""
    return InternalPaymentPayload(
        bank_txn_id=str(payload.id),
        order_code=extract_order_code(payload, order_code_regex),
        amount=payload.transfer_amount,
        received_at=parse_transaction_date(payload.transaction_date),
        raw=payload.model_dump(by_alias=True, mode="json"),
    )
