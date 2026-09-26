"""Cấu hình adapter, đọc từ biến môi trường / file .env (pydantic-settings)."""

from functools import lru_cache
from typing import Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Biến bắt buộc: DJANGO_INTERNAL_URL, INTERNAL_SERVICE_TOKEN, SEPAY_SECRET_KEY (IPN
    Cổng thanh toán — kênh chính V1). SEPAY_WEBHOOK_SECRET (webhook biến động số dư cũ)
    CHỈ bắt buộc khi SEPAY_BANK_WEBHOOK_ENABLED=true (mặc định TẮT, hồ sơ
    2026-09-26-sepay-cong-thanh-toan, quyết định Duy: giữ code, không dùng ở V1).
    Các biến còn lại có default hợp lý, có thể override qua env khi cần.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    django_internal_url: str = Field(
        description="Base URL Django nội bộ, vd: http://127.0.0.1:8000 (không cần dấu / cuối)."
    )
    internal_service_token: str = Field(
        description="Giá trị gửi kèm header X-Internal-Token khi adapter gọi Django."
    )
    sepay_secret_key: str = Field(
        description=(
            "Secret xác thực IPN Cổng thanh toán SePay, so khớp hằng-thời-gian với "
            "header X-Secret-Key (kênh chính V1, POST /ipn/sepay)."
        )
    )

    sepay_bank_webhook_enabled: bool = Field(
        default=False,
        description=(
            "Bật/tắt route cũ POST /webhook/sepay (webhook biến động số dư ngân hàng). "
            "Mặc định TẮT ở V1 — Duy chốt chỉ dùng IPN Cổng thanh toán. Giữ code, không xoá."
        ),
    )
    sepay_webhook_secret: Optional[str] = Field(
        default=None,
        description=(
            "Secret xác thực webhook SePay cũ (Authorization: Apikey <secret>). Chỉ bắt buộc "
            "khi SEPAY_BANK_WEBHOOK_ENABLED=true."
        ),
    )

    order_code_regex: str = Field(
        default=r"[A-Z]{1,4}[0-9]{4,}",
        description=(
            "Regex dự phòng rút mã đơn hàng từ nội dung chuyển khoản khi SePay "
            "không tự nhận diện được vào field `code`."
        ),
    )
    django_request_timeout_seconds: float = Field(default=10.0)
    django_request_retries: int = Field(
        default=2, description="Số lần thử lại (ngoài lần đầu) khi lỗi mạng/timeout/5xx tới Django."
    )

    @model_validator(mode="after")
    def _webhook_secret_required_when_enabled(self) -> "Settings":
        """Route cũ bật (SEPAY_BANK_WEBHOOK_ENABLED=true) thì bắt buộc có secret — fail-fast
        lúc khởi động thay vì fail âm thầm lúc request. Route tắt (mặc định V1) thì KHÔNG
        bắt buộc (P2-AC8)."""
        if self.sepay_bank_webhook_enabled and not (self.sepay_webhook_secret or "").strip():
            raise ValueError(
                "SEPAY_WEBHOOK_SECRET bắt buộc khi SEPAY_BANK_WEBHOOK_ENABLED=true."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Cache 1 instance Settings cho vòng đời process (đọc env 1 lần)."""
    return Settings()
