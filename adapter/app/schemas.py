"""
Pydantic schema cho payload SePay (vào) và payload nội bộ gửi cho Django (ra).

Nguồn tham khảo payload SePay: tài liệu công khai "Tích hợp Webhooks" của SePay
(https://docs.sepay.vn/tich-hop-webhooks.html), phần "Payload". Ví dụ payload
thực tế SePay gửi (POST JSON, transferType="in" khi có tiền vào tài khoản):

    {
        "id": 92704,
        "gateway": "Vietcombank",
        "transactionDate": "2024-07-02 11:08:33",
        "accountNumber": "1017588888",
        "subAccount": "",
        "code": "SEVN63DC8E5C",
        "content": "SEVN63DC8E5C chuyen tien",
        "transferType": "in",
        "description": "NGUYEN VAN A chuyen tien",
        "transferAmount": 5000000,
        "accumulated": 105000000,
        "referenceCode": "FT24012345678"
    }

GIẢ ĐỊNH quan trọng (ghi rõ vì không có tài khoản SePay thật để đối chiếu 1:1
lúc build; chỉnh lại schema này nếu Lộc gửi payload thật khác):
- `bank_txn_id` gửi Django = `referenceCode` (mã FT… ngân hàng in trên sao kê, cũng là
  mã Chủ gõ khi xác nhận tay) đã chuẩn hoá (bỏ khoảng trắng, viết hoa) — QA L7 · B12.
  `id` (số nguyên nội bộ SePay, KHÔNG in trên sao kê) chỉ là dự phòng khi referenceCode
  trống; luôn được giữ trong `raw`.
- `code`: khi Cảng Cá Lộc cấu hình sẵn "mã hoá đơn"/tiền tố nhận diện trên
  dashboard SePay (mục Cấu hình chung), SePay tự nhận diện mã đơn hàng nằm
  trong nội dung chuyển khoản và trả về ở field này (xem ví dụ trên: SePay tự
  nhận diện "SEVN63DC8E5C" từ content). Adapter ưu tiên dùng field này để suy
  ra `order_code`; nếu Lộc CHƯA cấu hình (field rỗng/null) thì fallback dò
  bằng regex trong `content`/`description` (xem app/sepay.py).
- `transferType` chỉ xử lý "in" (tiền vào). Giao dịch "out" bị bỏ qua ngay
  tại adapter (trả 200 nhưng không forward Django) vì không phải thanh toán
  của khách — đây không phải business rule của lõi mà là housekeeping của
  webhook (SePay có thể bắn cả 2 chiều nếu không lọc trên dashboard).
"""

from __future__ import annotations

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# SePay tài liệu ví dụ dùng format "YYYY-MM-DD HH:MM:SS" (giờ VN, không có timezone).
SEPAY_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

AMOUNT_QUANT = Decimal("0.01")
AMOUNT_MIN = Decimal("1")


def parse_sepay_datetime(raw: str) -> datetime:
    """transactionDate SePay → datetime. Nhận "YYYY-MM-DD HH:MM:SS" hoặc ISO 8601; sai → ValueError."""
    try:
        return datetime.strptime(raw, SEPAY_DATE_FORMAT)
    except ValueError:
        return datetime.fromisoformat(raw)


class SePayWebhookPayload(BaseModel):
    """Payload webhook SePay gửi tới adapter."""

    model_config = ConfigDict(populate_by_name=True)

    id: int
    gateway: str
    transaction_date: str = Field(alias="transactionDate")
    account_number: str = Field(alias="accountNumber")
    sub_account: Optional[str] = Field(default=None, alias="subAccount")
    code: Optional[str] = None
    content: str = ""
    transfer_type: str = Field(alias="transferType")
    description: Optional[str] = ""
    # B7: NaN/±Infinity bị pydantic chặn ngay (allow_inf_nan=False) → 400, không tới validator.
    transfer_amount: Decimal = Field(alias="transferAmount", allow_inf_nan=False)
    accumulated: Optional[Decimal] = None
    reference_code: Optional[str] = Field(default=None, alias="referenceCode")

    @field_validator("transfer_amount")
    @classmethod
    def amount_must_be_positive(cls, value: Decimal) -> Decimal:
        if not value.is_finite() or value <= 0:
            raise ValueError("transferAmount phải > 0")
        # L8 (BR-TT-08, quyết định Duy 2026-09-26): VND không có số lẻ → tối thiểu 1đ, so SAU
        # khi làm tròn 0,01 ROUND_HALF_UP (cùng cách Django `validate_amount`). Không đổi giá
        # trị gửi đi — Django tự làm tròn.
        if value < AMOUNT_MIN and value.quantize(AMOUNT_QUANT, rounding=ROUND_HALF_UP) < AMOUNT_MIN:
            raise ValueError("transferAmount tối thiểu 1đ")
        return value

    @field_validator("transaction_date")
    @classmethod
    def transaction_date_parsable(cls, value: str) -> str:
        # N-7 / B7: ngày hỏng trước đây nổ ở to_internal_payload → 500, SePay gửi lại mãi.
        try:
            parse_sepay_datetime(value)
        except (TypeError, ValueError):
            raise ValueError("transactionDate phải dạng 'YYYY-MM-DD HH:MM:SS' hoặc ISO 8601") from None
        return value

    @field_validator("transfer_type")
    @classmethod
    def transfer_type_not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("transferType không được rỗng")
        return value


class InternalPaymentPayload(BaseModel):
    """
    Body nội bộ gửi cho Django, đúng Contract B:
    POST {DJANGO_INTERNAL_URL}/api/internal/payments/sepay-webhook/
    body {bank_txn_id, order_code, amount, received_at, raw:{...}}
    """

    bank_txn_id: str
    order_code: str
    amount: Decimal
    received_at: str  # ISO 8601, xem app/sepay.py:parse_transaction_date
    raw: dict[str, Any]


# --- IPN Cổng thanh toán SePay (hồ sơ 2026-09-26-sepay-cong-thanh-toan, story P2) --------
#
# Tài liệu tham khảo: https://developer.sepay.vn/vi/cong-thanh-toan/IPN (tóm tắt do điều
# phối viên cung cấp trong phiên — KHÔNG có tài khoản Cổng thanh toán thật để đối chiếu
# payload 1:1 lúc build; Q4 trong 01-analysis.md vẫn ĐỎ). Payload mô tả:
#
#   {
#     "notification_type": "ORDER_PAID" | "TRANSACTION_VOID",
#     "order": {
#       "order_invoice_number": "SO260926-A1B2C3",
#       "amount": 540000,
#       "currency": "VND",
#       "status": "CAPTURED",
#       ...
#     },
#     "transaction": {
#       "id": 999888,
#       "reference_code": "FT26092612345",
#       ...
#     },
#     "customer": {...}
#   }
#
# GIẢ ĐỊNH (ghi rõ để BE/Duy đối chiếu khi có payload sandbox thật — xem 03-dev-notes.md
# mục "P2 (adapter)"):
# - Tên field con trong `transaction` chưa chắc đúng 100%. Adapter dò một danh sách tên
#   field ứng viên (ưu tiên mã tham chiếu ngân hàng FT… nếu có, theo Q4/BR-TT-03), xem
#   `app/sepay.py:pick_ipn_transaction_reference`.
# - `order`/`transaction` để `extra="allow"` (không chặn field lạ) vì tài liệu có thể có
#   thêm field SePay không liệt kê ở đây.
class SePayIpnOrder(BaseModel):
    """Sub-object `order` trong payload IPN. Field khác ngoài 4 field dưới bị bỏ qua
    (không cần cho việc map sang payload nội bộ), nhưng KHÔNG bị chặn (extra="allow")."""

    model_config = ConfigDict(extra="allow")

    order_invoice_number: Optional[str] = None
    amount: Optional[Decimal] = Field(default=None, allow_inf_nan=False)
    currency: Optional[str] = None
    status: Optional[str] = None


class SePayIpnPayload(BaseModel):
    """Payload IPN Cổng thanh toán SePay gửi tới `POST /ipn/sepay`."""

    model_config = ConfigDict(extra="allow")

    notification_type: str
    order: SePayIpnOrder
    transaction: dict[str, Any] = Field(default_factory=dict)
    customer: Optional[dict[str, Any]] = None
