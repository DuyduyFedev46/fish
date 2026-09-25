"""Transform payload SePay -> body nội bộ cho Django. Không có logic nghiệp vụ
(idempotency, khớp đơn, v.v.) ở đây — tất cả nằm ở Django (sales.confirm_payment),
đúng nguyên tắc "adapter là lớp mỏng" (ecosystem-l1.md mục 3)."""

from __future__ import annotations

import re

from .schemas import InternalPaymentPayload, SePayWebhookPayload, parse_sepay_datetime


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
