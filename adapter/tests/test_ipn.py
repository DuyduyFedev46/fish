"""Test cho POST /ipn/sepay — IPN Cổng thanh toán SePay (story P2, hồ sơ
2026-09-26-sepay-cong-thanh-toan). Tên test mang mã AC (P2-ACx)."""

import json

import httpx
import pytest
import respx

from tests.conftest import (
    DJANGO_IPN_ENDPOINT,
    INTERNAL_SERVICE_TOKEN,
    IPN_SECRET_HEADER,
    SEPAY_SECRET_KEY,
)


# --- P2-AC1: IPN hợp lệ -> map & forward Django, trả 200 -----------------------------

@respx.mock
def test_p2_ac1_order_paid_captured_vnd_forwards_to_django_and_returns_200(client, valid_sepay_ipn_payload):
    route = respx.post(DJANGO_IPN_ENDPOINT).mock(
        return_value=httpx.Response(200, json={"matched": True, "order_status": "PROCESSING"})
    )

    resp = client.post("/ipn/sepay", json=valid_sepay_ipn_payload, headers=IPN_SECRET_HEADER)

    assert resp.status_code == 200
    assert resp.json() == {"matched": True, "order_status": "PROCESSING"}

    assert route.called
    sent_request = route.calls.last.request
    assert sent_request.headers["x-internal-token"] == INTERNAL_SERVICE_TOKEN

    sent_body = json.loads(sent_request.content)
    assert set(sent_body.keys()) == {"bank_txn_id", "order_code", "amount", "received_at", "raw"}
    assert sent_body["bank_txn_id"] == "FT26092612345"
    assert sent_body["order_code"] == "SO260926-A1B2C3"
    assert float(sent_body["amount"]) == 540000
    assert sent_body["received_at"] == "2026-09-26T10:15:00+07:00"
    assert sent_body["raw"]["notification_type"] == "ORDER_PAID"
    assert sent_body["raw"]["order"]["order_invoice_number"] == "SO260926-A1B2C3"


@respx.mock
def test_p2_ac1_order_code_retry_suffix_is_stripped(client, valid_sepay_ipn_payload):
    """Q5: thanh toán lại có thể mang hậu tố lần thử -> bóc trước khi gửi Django."""
    route = respx.post(DJANGO_IPN_ENDPOINT).mock(return_value=httpx.Response(200, json={}))
    payload = dict(valid_sepay_ipn_payload)
    payload["order"] = dict(payload["order"], order_invoice_number="SO260926-A1B2C3-2")

    resp = client.post("/ipn/sepay", json=payload, headers=IPN_SECRET_HEADER)

    assert resp.status_code == 200
    sent_body = json.loads(route.calls.last.request.content)
    assert sent_body["order_code"] == "SO260926-A1B2C3"


@respx.mock
def test_p2_ac1_reference_code_missing_falls_back_to_transaction_id(client, valid_sepay_ipn_payload):
    route = respx.post(DJANGO_IPN_ENDPOINT).mock(return_value=httpx.Response(200, json={}))
    payload = dict(valid_sepay_ipn_payload)
    payload["transaction"] = {"id": 777001, "amount": 540000}

    resp = client.post("/ipn/sepay", json=payload, headers=IPN_SECRET_HEADER)

    assert resp.status_code == 200
    sent_body = json.loads(route.calls.last.request.content)
    assert sent_body["bank_txn_id"] == "777001"


# --- P2-AC2: sai/thiếu X-Secret-Key -> 401, không gọi Django, log không chứa khoá ----

@respx.mock
def test_p2_ac2_wrong_secret_key_returns_401_and_does_not_call_django(client, valid_sepay_ipn_payload):
    route = respx.post(DJANGO_IPN_ENDPOINT).mock(return_value=httpx.Response(200, json={}))

    resp = client.post("/ipn/sepay", json=valid_sepay_ipn_payload, headers={"X-Secret-Key": "sai-khoa"})

    assert resp.status_code == 401
    assert not route.called
    assert "sai-khoa" not in resp.text
    assert SEPAY_SECRET_KEY not in resp.text


@respx.mock
def test_p2_ac2_missing_secret_key_returns_401(client, valid_sepay_ipn_payload):
    route = respx.post(DJANGO_IPN_ENDPOINT).mock(return_value=httpx.Response(200, json={}))

    resp = client.post("/ipn/sepay", json=valid_sepay_ipn_payload)

    assert resp.status_code == 401
    assert not route.called


def test_p2_ac2_log_khong_chua_gia_tri_khoa(client, valid_sepay_ipn_payload, caplog):
    caplog.set_level("WARNING")
    client.post("/ipn/sepay", json=valid_sepay_ipn_payload, headers={"X-Secret-Key": "sai-khoa-bi-mat"})
    for record in caplog.records:
        assert "sai-khoa-bi-mat" not in record.getMessage()
        assert SEPAY_SECRET_KEY not in record.getMessage()


# --- P2-AC3: IPN gửi lại 2 lần -> forward cả 2 lần, trả đúng kết quả Django (idempotent
# là việc của Django; adapter chỉ pass-through, không tự chặn lần 2) ------------------

@respx.mock
def test_p2_ac3_duplicate_ipn_forwards_both_times_returns_same_result(client, valid_sepay_ipn_payload):
    route = respx.post(DJANGO_IPN_ENDPOINT).mock(
        return_value=httpx.Response(200, json={"matched": True, "order_status": "PROCESSING"})
    )

    resp1 = client.post("/ipn/sepay", json=valid_sepay_ipn_payload, headers=IPN_SECRET_HEADER)
    resp2 = client.post("/ipn/sepay", json=valid_sepay_ipn_payload, headers=IPN_SECRET_HEADER)

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json() == resp2.json() == {"matched": True, "order_status": "PROCESSING"}
    assert route.call_count == 2  # Django tự chống trùng theo bank_txn_id (BR-TT-03)


# --- P2-AC4: Django timeout/5xx -> adapter KHÔNG trả 200 ------------------------------

@respx.mock
def test_p2_ac4_django_5xx_does_not_return_200(client, valid_sepay_ipn_payload):
    route = respx.post(DJANGO_IPN_ENDPOINT).mock(return_value=httpx.Response(500, text="boom"))

    resp = client.post("/ipn/sepay", json=valid_sepay_ipn_payload, headers=IPN_SECRET_HEADER)

    assert resp.status_code != 200
    assert resp.status_code == 502
    assert route.call_count == 2  # retry nhẹ (django_request_retries=1 trong test settings)


@respx.mock
def test_p2_ac4_django_network_error_does_not_return_200(client, valid_sepay_ipn_payload):
    respx.post(DJANGO_IPN_ENDPOINT).mock(side_effect=httpx.ConnectError("connection refused"))

    resp = client.post("/ipn/sepay", json=valid_sepay_ipn_payload, headers=IPN_SECRET_HEADER)

    assert resp.status_code != 200
    assert resp.status_code == 502


# --- P2-AC5: payload hỏng vĩnh viễn -> 400, không 500, log đủ để đối soát, không log khoá --

@respx.mock
def test_p2_ac5_missing_order_invoice_number_returns_400_not_500(client, valid_sepay_ipn_payload):
    route = respx.post(DJANGO_IPN_ENDPOINT).mock(return_value=httpx.Response(200, json={}))
    payload = dict(valid_sepay_ipn_payload)
    payload["order"] = dict(payload["order"], order_invoice_number=None)

    resp = client.post("/ipn/sepay", json=payload, headers=IPN_SECRET_HEADER)

    assert resp.status_code == 400
    assert not route.called


@respx.mock
def test_p2_ac5_missing_amount_returns_400_not_500(client, valid_sepay_ipn_payload):
    route = respx.post(DJANGO_IPN_ENDPOINT).mock(return_value=httpx.Response(200, json={}))
    payload = dict(valid_sepay_ipn_payload)
    payload["order"] = dict(payload["order"], order_amount=None)

    resp = client.post("/ipn/sepay", json=payload, headers=IPN_SECRET_HEADER)

    assert resp.status_code == 400
    assert not route.called


@respx.mock
def test_p2_ac5_missing_transaction_id_returns_400_not_500(client, valid_sepay_ipn_payload):
    route = respx.post(DJANGO_IPN_ENDPOINT).mock(return_value=httpx.Response(200, json={}))
    payload = dict(valid_sepay_ipn_payload)
    payload["transaction"] = {"amount": 540000}  # không id, không reference_code

    resp = client.post("/ipn/sepay", json=payload, headers=IPN_SECRET_HEADER)

    assert resp.status_code == 400
    assert not route.called


def test_p2_ac5_missing_order_object_entirely_returns_400_not_500(client):
    resp = client.post(
        "/ipn/sepay",
        json={"notification_type": "ORDER_PAID", "transaction": {"id": 1}},
        headers=IPN_SECRET_HEADER,
    )
    assert resp.status_code == 400


def test_p2_ac5_garbage_body_returns_400_not_500(client):
    resp = client.post("/ipn/sepay", json={"foo": "bar"}, headers=IPN_SECRET_HEADER)
    assert resp.status_code == 400


def test_p2_ac5_non_json_body_returns_400(client):
    resp = client.post(
        "/ipn/sepay",
        content=b"khong-phai-json",
        headers={**IPN_SECRET_HEADER, "Content-Type": "application/json"},
    )
    assert resp.status_code == 400


def test_p2_ac5_log_canh_bao_khong_chua_khoa(client, valid_sepay_ipn_payload, caplog):
    caplog.set_level("WARNING")
    payload = dict(valid_sepay_ipn_payload)
    payload["order"] = dict(payload["order"], order_invoice_number=None)

    client.post("/ipn/sepay", json=payload, headers=IPN_SECRET_HEADER)

    assert any("payload hỏng" in r.getMessage() for r in caplog.records)
    for record in caplog.records:
        assert SEPAY_SECRET_KEY not in record.getMessage()


# --- P2-AC6: ORDER_PAID nhưng order_status != CAPTURED hoặc order_currency != VND -> không
# xác nhận, ghi nhận (log), trả 200, KHÔNG gọi Django ----------------------------------

@respx.mock
def test_p2_ac6_status_not_captured_does_not_confirm_returns_200(client, valid_sepay_ipn_payload):
    route = respx.post(DJANGO_IPN_ENDPOINT).mock(return_value=httpx.Response(200, json={}))
    payload = dict(valid_sepay_ipn_payload)
    payload["order"] = dict(payload["order"], order_status="PENDING")

    resp = client.post("/ipn/sepay", json=payload, headers=IPN_SECRET_HEADER)

    assert resp.status_code == 200
    assert not route.called


@respx.mock
def test_p2_ac6_currency_not_vnd_does_not_confirm_returns_200(client, valid_sepay_ipn_payload):
    route = respx.post(DJANGO_IPN_ENDPOINT).mock(return_value=httpx.Response(200, json={}))
    payload = dict(valid_sepay_ipn_payload)
    payload["order"] = dict(payload["order"], order_currency="USD")

    resp = client.post("/ipn/sepay", json=payload, headers=IPN_SECRET_HEADER)

    assert resp.status_code == 200
    assert not route.called


@respx.mock
def test_p2_ac6_logs_for_chu_to_review(client, valid_sepay_ipn_payload, caplog):
    caplog.set_level("WARNING")
    route = respx.post(DJANGO_IPN_ENDPOINT).mock(return_value=httpx.Response(200, json={}))
    payload = dict(valid_sepay_ipn_payload)
    payload["order"] = dict(payload["order"], order_currency="USD")

    client.post("/ipn/sepay", json=payload, headers=IPN_SECRET_HEADER)

    assert not route.called
    assert any("status/currency" in r.getMessage() for r in caplog.records)


@respx.mock
def test_p2_ac6_transaction_status_not_approved_does_not_confirm_returns_200(
    client, valid_sepay_ipn_payload
):
    """transaction.transaction_status có mặt và khác APPROVED -> không xác nhận (dù
    order_status=CAPTURED, order_currency=VND đúng)."""
    route = respx.post(DJANGO_IPN_ENDPOINT).mock(return_value=httpx.Response(200, json={}))
    payload = dict(valid_sepay_ipn_payload)
    payload["transaction"] = dict(payload["transaction"], transaction_status="DECLINED")

    resp = client.post("/ipn/sepay", json=payload, headers=IPN_SECRET_HEADER)

    assert resp.status_code == 200
    assert not route.called


# --- P2-AC7: TRANSACTION_VOID -> 200, không đổi đơn/kho (không gọi Django), log cảnh báo --

@respx.mock
def test_p2_ac7_transaction_void_returns_200_and_does_not_call_django(client, valid_sepay_ipn_payload):
    route = respx.post(DJANGO_IPN_ENDPOINT).mock(return_value=httpx.Response(200, json={}))
    payload = dict(valid_sepay_ipn_payload, notification_type="TRANSACTION_VOID")

    resp = client.post("/ipn/sepay", json=payload, headers=IPN_SECRET_HEADER)

    assert resp.status_code == 200
    assert not route.called


def test_p2_ac7_transaction_void_logs_order_and_transaction_id_no_secret(
    client, valid_sepay_ipn_payload, caplog
):
    caplog.set_level("WARNING")
    payload = dict(valid_sepay_ipn_payload, notification_type="TRANSACTION_VOID")

    client.post("/ipn/sepay", json=payload, headers=IPN_SECRET_HEADER)

    messages = [r.getMessage() for r in caplog.records]
    assert any("TRANSACTION_VOID" in m and "SO260926-A1B2C3" in m and "FT26092612345" in m for m in messages)
    for m in messages:
        assert SEPAY_SECRET_KEY not in m


# --- P2-AC8: route webhook cũ TẮT theo mặc định V1 -> không xử lý, không gọi Django;
# code + test cũ vẫn chạy khi BẬT cấu hình (xem tests/test_webhook.py, dùng fixture
# `client` với sepay_bank_webhook_enabled=True) ---------------------------------------

@respx.mock
def test_p2_ac8_webhook_cu_tat_mac_dinh_tra_loi_tu_choi_khong_goi_django(
    client_default_config, valid_sepay_payload
):
    from tests.conftest import DJANGO_WEBHOOK_ENDPOINT

    route = respx.post(DJANGO_WEBHOOK_ENDPOINT).mock(return_value=httpx.Response(200, json={}))

    resp = client_default_config.post(
        "/webhook/sepay", json=valid_sepay_payload, headers={"Authorization": "Apikey khong-quan-trong"}
    )

    assert resp.status_code in (403, 404)
    assert not route.called


def test_p2_ac8_startup_khong_bat_buoc_sepay_webhook_secret_khi_tat(client_default_config):
    """Khởi động (tạo Settings) thành công dù không có SEPAY_WEBHOOK_SECRET, vì route cũ
    tắt (sepay_bank_webhook_enabled=False mặc định) — xem tests/conftest.py TEST_SETTINGS_DEFAULT."""
    resp = client_default_config.get("/healthz")
    assert resp.status_code == 200


def test_p2_ac8_bat_cau_hinh_thi_startup_that_bai_neu_thieu_secret():
    from app.config import Settings

    with pytest.raises(Exception):
        Settings(
            django_internal_url="http://django.test",
            internal_service_token="x",
            sepay_secret_key="y",
            sepay_bank_webhook_enabled=True,
            sepay_webhook_secret=None,
        )


# --- P2-AC9: healthz -----------------------------------------------------------------

def test_p2_ac9_healthz_200(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# --- Test phân quyền/an toàn bổ sung: notification_type lạ -> log, 200, không gọi Django --

@respx.mock
def test_ipn_notification_type_la_khong_bi_treo_tra_200_khong_goi_django(client, valid_sepay_ipn_payload):
    route = respx.post(DJANGO_IPN_ENDPOINT).mock(return_value=httpx.Response(200, json={}))
    payload = dict(valid_sepay_ipn_payload, notification_type="SOMETHING_ELSE")

    resp = client.post("/ipn/sepay", json=payload, headers=IPN_SECRET_HEADER)

    assert resp.status_code == 200
    assert not route.called
