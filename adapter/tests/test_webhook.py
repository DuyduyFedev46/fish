import json

import httpx
import respx

from tests.conftest import AUTH_HEADER, DJANGO_WEBHOOK_ENDPOINT, INTERNAL_SERVICE_TOKEN


def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@respx.mock
def test_webhook_valid_forwards_correct_shape_and_header(client, valid_sepay_payload):
    """Webhook hợp lệ -> forward đúng shape {bank_txn_id, order_code, amount,
    received_at, raw} tới Django, kèm header X-Internal-Token, trả 200 với
    đúng body Django trả về."""
    route = respx.post(DJANGO_WEBHOOK_ENDPOINT).mock(
        return_value=httpx.Response(200, json={"matched": True, "order_status": "PAID"})
    )

    resp = client.post("/webhook/sepay", json=valid_sepay_payload, headers=AUTH_HEADER)

    assert resp.status_code == 200
    assert resp.json() == {"matched": True, "order_status": "PAID"}

    assert route.called
    sent_request = route.calls.last.request
    assert sent_request.headers["x-internal-token"] == INTERNAL_SERVICE_TOKEN

    sent_body = json.loads(sent_request.content)
    assert set(sent_body.keys()) == {"bank_txn_id", "order_code", "amount", "received_at", "raw"}
    assert sent_body["bank_txn_id"] == "92704"
    assert sent_body["order_code"] == "DH000123"
    assert float(sent_body["amount"]) == 500000
    assert sent_body["raw"]["id"] == 92704
    assert sent_body["raw"]["transferType"] == "in"


@respx.mock
def test_webhook_order_code_fallback_regex_from_content(client, valid_sepay_payload):
    """Khi SePay chưa nhận diện được `code` (null), adapter fallback dò
    order_code bằng regex trong nội dung chuyển khoản."""
    payload = dict(valid_sepay_payload)
    payload["code"] = None
    payload["content"] = "chuyen tien don hang DH009988 cam on"

    route = respx.post(DJANGO_WEBHOOK_ENDPOINT).mock(
        return_value=httpx.Response(200, json={"matched": True, "order_status": "PAID"})
    )

    resp = client.post("/webhook/sepay", json=payload, headers=AUTH_HEADER)

    assert resp.status_code == 200
    sent_body = json.loads(route.calls.last.request.content)
    assert sent_body["order_code"] == "DH009988"


def test_webhook_wrong_secret_returns_401(client, valid_sepay_payload):
    resp = client.post(
        "/webhook/sepay", json=valid_sepay_payload, headers={"Authorization": "Apikey sai-secret"}
    )
    assert resp.status_code == 401


def test_webhook_missing_secret_returns_401(client, valid_sepay_payload):
    resp = client.post("/webhook/sepay", json=valid_sepay_payload)
    assert resp.status_code == 401


def test_webhook_garbage_payload_returns_400(client):
    resp = client.post("/webhook/sepay", json={"foo": "bar"}, headers=AUTH_HEADER)
    assert resp.status_code == 400


def test_webhook_non_json_body_returns_400(client):
    resp = client.post(
        "/webhook/sepay",
        content=b"khong-phai-json",
        headers={**AUTH_HEADER, "Content-Type": "application/json"},
    )
    assert resp.status_code == 400


@respx.mock
def test_webhook_django_5xx_returns_502(client, valid_sepay_payload):
    route = respx.post(DJANGO_WEBHOOK_ENDPOINT).mock(return_value=httpx.Response(500, text="boom"))

    resp = client.post("/webhook/sepay", json=valid_sepay_payload, headers=AUTH_HEADER)

    assert resp.status_code == 502
    # đã retry nhẹ (django_request_retries=1 trong test settings -> tổng 2 lần gọi)
    assert route.call_count == 2


@respx.mock
def test_webhook_django_network_error_returns_502(client, valid_sepay_payload):
    respx.post(DJANGO_WEBHOOK_ENDPOINT).mock(side_effect=httpx.ConnectError("connection refused"))

    resp = client.post("/webhook/sepay", json=valid_sepay_payload, headers=AUTH_HEADER)

    assert resp.status_code == 502


@respx.mock
def test_webhook_outgoing_transfer_is_skipped_without_forwarding(client, valid_sepay_payload):
    """Giao dịch transferType='out' không phải thanh toán của khách -> bỏ
    qua, KHÔNG forward Django, vẫn trả 200 để SePay không retry vô ích."""
    route = respx.post(DJANGO_WEBHOOK_ENDPOINT).mock(return_value=httpx.Response(200, json={}))
    payload = dict(valid_sepay_payload)
    payload["transferType"] = "out"

    resp = client.post("/webhook/sepay", json=payload, headers=AUTH_HEADER)

    assert resp.status_code == 200
    assert resp.json()["skipped"] is True
    assert not route.called
