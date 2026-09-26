"""
FastAPI adapter cho Cảng Cá Lộc — Contract C (BUILD-PLAN.md).

Lớp MỎNG: không đụng DB/ORM. Chỉ nhận webhook SePay -> validate/transform ->
gọi API nội bộ Django (/api/internal/payments/sepay-webhook/) kèm
X-Internal-Token. Idempotency theo bank_txn_id là việc của Django
(sales.confirm_payment) — adapter chỉ forward.

Cô lập lỗi theo yêu cầu:
- payload sai (không parse được theo schema SePay) -> 400
- thiếu/sai secret webhook -> 401
- Django trả 4xx do DỮ LIỆU (400/404/409/422, vd số tiền ngoài miền — QA L7 · B13) ->
  trả lại đúng mã đó + body Django, không retry, để SePay không gửi lại mãi
- Django 401/403 (token nội bộ sai = cấu hình phía mình), mạng/timeout/5xx -> 502
  (SePay gửi lại sau, không nuốt mất khoản tiền)
"""

from __future__ import annotations

import hmac
import logging

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .config import Settings, get_settings
from .schemas import SePayIpnPayload, SePayWebhookPayload
from .sepay import (
    IpnMalformedError,
    is_incoming_transfer,
    is_ipn_order_paid,
    is_ipn_status_confirmable,
    is_ipn_transaction_void,
    to_internal_payload,
    to_internal_payload_from_ipn,
)

logger = logging.getLogger("adapter")

# Contract nội bộ cho IPN Cổng thanh toán — GIẢ ĐỊNH (chưa có dev-notes phía Django lúc
# code adapter, hồ sơ 2026-09-26-sepay-cong-thanh-toan story P2/P3 làm song song). Endpoint
# RIÊNG với `/api/internal/payments/sepay-webhook/` (webhook ngân hàng cũ) để Django phân
# biệt được nguồn "Cổng SePay" (BR-TT-15/P3-AC1) ngay từ URL, không cần thêm field `source`
# vào body. Ghi rõ trong 03-dev-notes.md để đối chiếu với agent làm P3.
DJANGO_IPN_ENDPOINT_PATH = "/api/internal/payments/sepay-ipn/"

app = FastAPI(
    title="Cảng Cá Lộc - Adapter",
    description="Lớp adapter mỏng nhận webhook SePay, forward vào Django nội bộ.",
    version="1.0.0",
)


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


def _verify_sepay_secret(authorization: str | None, settings: Settings) -> None:
    """
    Xác thực webhook bằng HEADER `Authorization: Apikey <SEPAY_WEBHOOK_SECRET>`.

    Chọn header (thay vì field trong body) vì đây đúng cơ chế "API Key" mà
    SePay hỗ trợ cấu hình sẵn trên dashboard (mục Cấu hình Webhooks — 1 trong
    4 phương thức: HMAC-SHA256 / API Key / OAuth2 / không xác thực). Header
    tách biệt khỏi business payload nên validate được độc lập, không phụ
    thuộc payload có parse được hay không.
    """
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Thiếu header Authorization")

    expected = settings.sepay_webhook_secret or ""
    parts = authorization.split(None, 1)
    # So hằng-thời-gian (R5/BR-TT-13): tránh lộ độ dài khớp qua thời gian phản hồi. Secret
    # rỗng (chưa cấu hình) -> luôn từ chối, không so `parts[1] == ""`.
    if (
        len(parts) != 2
        or parts[0].lower() != "apikey"
        or not expected
        or not hmac.compare_digest(parts[1].encode("utf-8"), expected.encode("utf-8"))
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sai SePay webhook secret")


def _verify_sepay_ipn_secret(secret_header: str | None, settings: Settings) -> None:
    """Xác thực IPN Cổng thanh toán bằng header `X-Secret-Key`, so hằng-thời-gian
    (hmac.compare_digest) với `SEPAY_SECRET_KEY` (P2-AC2, BR-TT-13). Log KHÔNG chứa giá
    trị khoá — chỉ log sự kiện "sai khoá"."""
    expected = settings.sepay_secret_key or ""
    if (
        not secret_header
        or not expected
        or not hmac.compare_digest(secret_header.encode("utf-8"), expected.encode("utf-8"))
    ):
        logger.warning("IPN SePay: thiếu hoặc sai X-Secret-Key")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sai hoặc thiếu X-Secret-Key")


# 4xx do dữ liệu webhook → trả nguyên cho SePay; 401/403 là lỗi cấu hình nội bộ → 502.
_PASS_THROUGH_4XX = {400, 404, 409, 422}


def _json_or_text(response: httpx.Response):
    try:
        return response.json()
    except ValueError:
        return response.text


async def _forward_to_django(
    body: dict,
    settings: Settings,
    endpoint_path: str = "/api/internal/payments/sepay-webhook/",
) -> dict:
    """
    POST body nội bộ tới Django, kèm X-Internal-Token. Retry nhẹ (mặc định 2
    lần thêm, tổng 3 lần thử) khi lỗi mạng/timeout hoặc Django trả 5xx — để
    SePay không phải retry ngay lập tức khi lỗi chỉ là tạm thời phía Django.
    Lỗi 4xx từ Django coi là không tạm thời -> không retry. 400/404/409/422 (dữ liệu sai)
    -> HTTPException cùng mã; còn lại thất bại cuối cùng -> HTTPException 502.
    """
    url = f"{settings.django_internal_url.rstrip('/')}{endpoint_path}"
    headers = {"X-Internal-Token": settings.internal_service_token}

    attempts = settings.django_request_retries + 1
    last_error = "không rõ"

    async with httpx.AsyncClient(timeout=settings.django_request_timeout_seconds) as client:
        for attempt in range(1, attempts + 1):
            try:
                response = await client.post(url, json=body, headers=headers)
            except httpx.RequestError as exc:
                last_error = f"lỗi mạng/timeout khi gọi Django: {exc}"
                logger.warning("Gọi Django thất bại (lần %s/%s): %s", attempt, attempts, exc)
                continue

            if response.status_code < 300:
                try:
                    return response.json()
                except ValueError:
                    return {"raw_response": response.text}

            last_error = f"Django trả HTTP {response.status_code}: {response.text}"
            logger.warning("Django lỗi (lần %s/%s): %s", attempt, attempts, last_error)

            if response.status_code in _PASS_THROUGH_4XX:
                # B13: dữ liệu sai vĩnh viễn -> trả đúng mã 4xx, không retry, không 502.
                raise HTTPException(status_code=response.status_code, detail=_json_or_text(response))
            if response.status_code < 500:
                # 401/403/...: token/cấu hình sai -> retry vô ích, trả 502 bên dưới.
                break

    raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Gọi Django nội bộ thất bại: {last_error}")


@app.post("/webhook/sepay")
async def webhook_sepay(
    request: Request,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    # BR-TT-15/P2-AC8 (quyết định Duy 2026-09-26): webhook biến động số dư KHÔNG dùng ở V1.
    # Tắt bằng cấu hình, mặc định TẮT. Route giữ nguyên code + test (bật cấu hình để chạy).
    if not settings.sepay_bank_webhook_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook biến động số dư đang tắt (SEPAY_BANK_WEBHOOK_ENABLED=false).",
        )

    _verify_sepay_secret(authorization, settings)

    try:
        raw_body = await request.json()
    except Exception as exc:  # noqa: BLE001 - body không phải JSON hợp lệ
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Body không phải JSON hợp lệ") from exc

    try:
        payload = SePayWebhookPayload.model_validate(raw_body)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            # B7: ctx/input của pydantic có thể chứa ValueError/Decimal → không JSON được → 500.
            detail={
                "message": "Payload SePay không hợp lệ",
                "errors": exc.errors(include_context=False, include_input=False, include_url=False),
            },
        ) from exc

    if not is_incoming_transfer(payload):
        logger.info("Bỏ qua giao dịch không phải tiền vào: id=%s transferType=%s", payload.id, payload.transfer_type)
        return JSONResponse(status_code=200, content={"skipped": True, "reason": "not-incoming-transfer"})

    internal_payload = to_internal_payload(payload, settings.order_code_regex)
    django_result = await _forward_to_django(internal_payload.model_dump(mode="json"), settings)

    return JSONResponse(status_code=200, content=django_result)


def _ipn_order_code(raw_body: dict) -> str:
    """Best-effort lấy order_invoice_number để LOG (không raise) — dùng khi payload có thể
    thiếu field, ví dụ log cảnh báo E9/void."""
    order = raw_body.get("order")
    if isinstance(order, dict):
        return str(order.get("order_invoice_number") or "")
    return ""


def _ipn_transaction_id(raw_body: dict) -> str:
    """Best-effort lấy id giao dịch để LOG (không raise)."""
    transaction = raw_body.get("transaction")
    if isinstance(transaction, dict):
        for key in ("reference", "reference_code", "reference_number", "transaction_id", "id"):
            value = transaction.get(key)
            if value:
                return str(value)
    return ""


@app.post("/ipn/sepay")
async def ipn_sepay(
    request: Request,
    x_secret_key: str | None = Header(default=None, alias="X-Secret-Key"),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """IPN Cổng thanh toán SePay (BR-TT-02, story P2, hồ sơ
    2026-09-26-sepay-cong-thanh-toan). Kênh CHÍNH V1 xác nhận thanh toán.

    - `X-Secret-Key` sai/thiếu -> 401, KHÔNG gọi Django, KHÔNG log giá trị khoá (P2-AC2).
    - `TRANSACTION_VOID` -> 200, chỉ log cảnh báo, KHÔNG đổi đơn/kho (BR-TT-16, P2-AC7).
    - `ORDER_PAID` + `order.order_status=CAPTURED` + `order.order_currency=VND` (+
      `transaction.transaction_status=APPROVED` nếu field này có mặt) -> map & gọi Django,
      trả nguyên kết quả Django (P2-AC1, P2-AC3 idempotent do Django lo).
    - `ORDER_PAID` với status/currency/transaction_status khác -> 200, chỉ ghi log, KHÔNG
      gọi Django (Q9/P2-AC6).
    - Payload hỏng vĩnh viễn (thiếu mã đơn/số tiền/mã giao dịch) -> 400, KHÔNG 500, log đủ
      để đối soát, không log khoá (E9/P2-AC5).
    - Django lỗi mạng/timeout/5xx -> không trả 200 cho SePay (SePay gửi lại, P2-AC4).
    """
    _verify_sepay_ipn_secret(x_secret_key, settings)

    try:
        raw_body = await request.json()
    except Exception as exc:  # noqa: BLE001 - body không phải JSON hợp lệ
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Body không phải JSON hợp lệ") from exc

    if not isinstance(raw_body, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Body IPN phải là object JSON")

    try:
        payload = SePayIpnPayload.model_validate(raw_body)
    except ValidationError as exc:
        logger.warning(
            "IPN SePay: payload hỏng (thiếu field bắt buộc) order_code=%s transaction_id=%s",
            _ipn_order_code(raw_body),
            _ipn_transaction_id(raw_body),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Payload IPN SePay không hợp lệ",
                "errors": exc.errors(include_context=False, include_input=False, include_url=False),
            },
        ) from exc

    if is_ipn_transaction_void(payload):
        # BR-TT-16 (V1 chỉ VietQR, void gần như không xảy ra): không tự đổi đơn/kho —
        # chứng từ không xoá (BR-PQ-10), huỷ đơn đã thanh toán là quyền của Chủ. Chỉ log
        # cảnh báo để Duy/Chủ đối chiếu dashboard SePay và xử lý tay theo P-07 nếu cần.
        logger.warning(
            "IPN SePay TRANSACTION_VOID: order_code=%s transaction_id=%s — cần Chủ đối chiếu (BR-TT-16)",
            _ipn_order_code(raw_body),
            _ipn_transaction_id(raw_body),
        )
        return JSONResponse(status_code=200, content={"acknowledged": True, "action": "void_logged"})

    if not is_ipn_order_paid(payload):
        # notification_type lạ ngoài 2 giá trị tài liệu mô tả -> không xác nhận, chỉ log,
        # trả 200 để không gây SePay gửi lại vô hạn (tinh thần giống Q9).
        logger.warning(
            "IPN SePay notification_type lạ '%s': order_code=%s — không xác nhận",
            payload.notification_type,
            _ipn_order_code(raw_body),
        )
        return JSONResponse(status_code=200, content={"acknowledged": True, "action": "ignored_unknown_type"})

    if not is_ipn_status_confirmable(payload):
        # Q9: order.order_status != CAPTURED, order.order_currency != VND, hoặc
        # transaction.transaction_status != APPROVED (khi có mặt) -> không tự xác nhận, ghi
        # nhận để Chủ xem (log), trả 200.
        logger.warning(
            "IPN SePay ORDER_PAID nhưng status/currency không hợp lệ để xác nhận: "
            "order_code=%s status=%s currency=%s",
            _ipn_order_code(raw_body),
            payload.order.effective_status,
            payload.order.effective_currency,
        )
        return JSONResponse(status_code=200, content={"acknowledged": True, "action": "ignored_status_or_currency"})

    try:
        internal_payload = to_internal_payload_from_ipn(payload)
    except IpnMalformedError as exc:
        # E9: payload hỏng vĩnh viễn — không gây vòng gửi lại vô hạn (400, không 500), log
        # đủ để đối soát, KHÔNG log khoá.
        logger.warning(
            "IPN SePay ORDER_PAID payload hỏng vĩnh viễn (%s): order_code=%s transaction_id=%s",
            exc,
            _ipn_order_code(raw_body),
            _ipn_transaction_id(raw_body),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    django_result = await _forward_to_django(
        internal_payload.model_dump(mode="json"), settings, endpoint_path=DJANGO_IPN_ENDPOINT_PATH
    )
    return JSONResponse(status_code=200, content=django_result)
