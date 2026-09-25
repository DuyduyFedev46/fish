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
- `id` là số nguyên, duy nhất phía SePay cho mỗi giao dịch -> dùng làm
  `bank_txn_id` chuyển cho Django (đủ ổn định để Django idempotent theo đó).
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

from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    transfer_amount: Decimal = Field(alias="transferAmount")
    accumulated: Optional[Decimal] = None
    reference_code: Optional[str] = Field(default=None, alias="referenceCode")

    @field_validator("transfer_amount")
    @classmethod
    def amount_must_be_positive(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("transferAmount phải > 0")
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
