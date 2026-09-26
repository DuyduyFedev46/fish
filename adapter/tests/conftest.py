import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app

DJANGO_INTERNAL_URL = "http://django.test"
INTERNAL_SERVICE_TOKEN = "internal-token-test"
SEPAY_WEBHOOK_SECRET = "sepay-secret-test"
SEPAY_SECRET_KEY = "sepay-ipn-secret-key-test"

DJANGO_WEBHOOK_ENDPOINT = f"{DJANGO_INTERNAL_URL}/api/internal/payments/sepay-webhook/"
DJANGO_IPN_ENDPOINT = f"{DJANGO_INTERNAL_URL}/api/internal/payments/sepay-ipn/"

AUTH_HEADER = {"Authorization": f"Apikey {SEPAY_WEBHOOK_SECRET}"}
IPN_SECRET_HEADER = {"X-Secret-Key": SEPAY_SECRET_KEY}

# P2-AC8: mặc định V1 route webhook cũ TẮT — dùng settings này (bank webhook enabled=True)
# chỉ cho các test dành riêng cho route cũ, để giữ nguyên hành vi/test đã có (41 test gốc).
TEST_SETTINGS = Settings(
    django_internal_url=DJANGO_INTERNAL_URL,
    internal_service_token=INTERNAL_SERVICE_TOKEN,
    sepay_secret_key=SEPAY_SECRET_KEY,
    sepay_bank_webhook_enabled=True,
    sepay_webhook_secret=SEPAY_WEBHOOK_SECRET,
    django_request_retries=1,  # test nhanh, không chờ retry lâu
)

# Cấu hình mặc định thật của V1: route webhook cũ TẮT, không cấu hình secret cũ.
TEST_SETTINGS_DEFAULT = Settings(
    django_internal_url=DJANGO_INTERNAL_URL,
    internal_service_token=INTERNAL_SERVICE_TOKEN,
    sepay_secret_key=SEPAY_SECRET_KEY,
    django_request_retries=1,
)


@pytest.fixture
def client():
    app.dependency_overrides[get_settings] = lambda: TEST_SETTINGS
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def client_default_config():
    """Client với cấu hình mặc định V1 (webhook cũ TẮT, không cần SEPAY_WEBHOOK_SECRET)."""
    app.dependency_overrides[get_settings] = lambda: TEST_SETTINGS_DEFAULT
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def valid_sepay_payload() -> dict:
    """Payload mẫu đúng dạng SePay thật (xem docstring app/schemas.py)."""
    return {
        "id": 92704,
        "gateway": "Vietcombank",
        "transactionDate": "2024-07-02 11:08:33",
        "accountNumber": "1017588888",
        "subAccount": "",
        "code": "DH000123",
        "content": "DH000123 chuyen tien mua hang",
        "transferType": "in",
        "description": "NGUYEN VAN A chuyen tien",
        "transferAmount": 500000,
        "accumulated": 105000000,
        "referenceCode": "FT24012345678",
    }


@pytest.fixture
def valid_sepay_ipn_payload() -> dict:
    """Payload IPN Cổng thanh toán mẫu — ORDER_PAID, CAPTURED, VND (xem docstring
    app/schemas.py:SePayIpnPayload về nguồn/giả định)."""
    return {
        "notification_type": "ORDER_PAID",
        "order": {
            "order_invoice_number": "SO260926-A1B2C3",
            "amount": 540000,
            "currency": "VND",
            "status": "CAPTURED",
        },
        "transaction": {
            "id": 999888,
            "reference_code": "FT26092612345",
            "amount": 540000,
            "paid_at": "2026-09-26T10:15:00+07:00",
        },
        "customer": {
            "name": "Nguyen Van A",
            "phone": "0900000000",
        },
    }
