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
    """Payload IPN Cổng thanh toán mẫu — ĐÚNG theo tài liệu SePay thật
    (https://developer.sepay.vn/vi/cong-thanh-toan/IPN), ORDER_PAID, CAPTURED, VND,
    transaction_status APPROVED (xem docstring app/schemas.py:SePayIpnOrder)."""
    return {
        "timestamp": 1757058220,
        "notification_type": "ORDER_PAID",
        "order": {
            "id": "e2c195be-1111-2222-3333-444455556666",
            "order_id": "NPSETVI00101000042R",
            "order_status": "CAPTURED",
            "order_currency": "VND",
            "order_amount": "540000.00",
            "order_invoice_number": "SO260926-A1B2C3",
            "custom_data": [],
            "user_agent": "Mozilla/5.0",
            "ip_address": "14.169.1.1",
            "order_description": "Thanh toan don hang SO260926-A1B2C3",
        },
        "transaction": {
            "id": "384c66dd-7777-8888-9999-aaaabbbbcccc",
            "payment_method": "BANK_TRANSFER",
            "transaction_id": "FT26092612345",
            "transaction_type": "PAYMENT",
            "transaction_date": "2026-09-26 10:15:00",
            "transaction_status": "APPROVED",
            "transaction_amount": "540000",
            "transaction_currency": "VND",
            "authentication_status": "AUTHENTICATION_SUCCESSFUL",
        },
        "customer": {
            "id": "bae12d2f-0000-1111-2222-333344445555",
            "customer_id": "CUST_001",
        },
    }
