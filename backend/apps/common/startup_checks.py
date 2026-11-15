"""
Kiểm cấu hình lúc khởi động web (M-4/B11, rà soát bảo mật 15/11).

`config/wsgi.py` gọi khi không DEBUG. Cố ý KHÔNG đặt trong settings: job nền (migrate, cancel_expired_orders)
chạy `manage.py` và không cần token nội bộ, nên không được dừng vì thiếu nó.
"""
from django.core.exceptions import ImproperlyConfigured

INTERNAL_TOKEN_MIN_LENGTH = 32
# Chuỗi mẫu công khai trong backend/.env.example và adapter/.env.example.
INTERNAL_TOKEN_PLACEHOLDERS = {"đổi-thành-token-nội-bộ", "doi-gia-tri-nay-thanh-secret-that"}  # naming: allow - chuỗi mẫu công khai trong .env.example


def validate_internal_service_token(token) -> None:
    """Token nội bộ (adapter -> Django, ghi tiền) phải đủ dài và không phải chuỗi mẫu."""
    value = (token or "").strip()
    if not value or len(value) < INTERNAL_TOKEN_MIN_LENGTH or value in INTERNAL_TOKEN_PLACEHOLDERS:
        raise ImproperlyConfigured(
            f"INTERNAL_SERVICE_TOKEN thiếu, ngắn hơn {INTERNAL_TOKEN_MIN_LENGTH} ký tự hoặc còn là chuỗi mẫu "
            "trong khi DJANGO_DEBUG tắt. Đặt token ngẫu nhiên dài (Secret Manager)."
        )
