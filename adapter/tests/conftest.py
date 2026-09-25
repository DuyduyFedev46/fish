import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app

DJANGO_INTERNAL_URL = "http://django.test"
INTERNAL_SERVICE_TOKEN = "internal-token-test"
SEPAY_WEBHOOK_SECRET = "sepay-secret-test"

DJANGO_WEBHOOK_ENDPOINT = f"{DJANGO_INTERNAL_URL}/api/internal/payments/sepay-webhook/"

AUTH_HEADER = {"Authorization": f"Apikey {SEPAY_WEBHOOK_SECRET}"}

TEST_SETTINGS = Settings(
    django_internal_url=DJANGO_INTERNAL_URL,
    internal_service_token=INTERNAL_SERVICE_TOKEN,
    sepay_webhook_secret=SEPAY_WEBHOOK_SECRET,
    django_request_retries=1,  # test nhanh, không chờ retry lâu
)


@pytest.fixture
def client():
    app.dependency_overrides[get_settings] = lambda: TEST_SETTINGS
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
