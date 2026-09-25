"""Cấu hình adapter, đọc từ biến môi trường / file .env (pydantic-settings)."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    3 biến bắt buộc theo Contract C (BUILD-PLAN.md):
    DJANGO_INTERNAL_URL, INTERNAL_SERVICE_TOKEN, SEPAY_WEBHOOK_SECRET.
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
    sepay_webhook_secret: str = Field(
        description="Secret xác thực webhook SePay, so khớp với header Authorization: Apikey <secret>."
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


@lru_cache
def get_settings() -> Settings:
    """Cache 1 instance Settings cho vòng đời process (đọc env 1 lần)."""
    return Settings()
