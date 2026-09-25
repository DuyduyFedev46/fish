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

import logging

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .config import Settings, get_settings
from .schemas import SePayWebhookPayload
from .sepay import is_incoming_transfer, to_internal_payload

logger = logging.getLogger("adapter")

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

    parts = authorization.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "apikey" or parts[1] != settings.sepay_webhook_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sai SePay webhook secret")


# 4xx do dữ liệu webhook → trả nguyên cho SePay; 401/403 là lỗi cấu hình nội bộ → 502.
_PASS_THROUGH_4XX = {400, 404, 409, 422}


def _json_or_text(response: httpx.Response):
    try:
        return response.json()
    except ValueError:
        return response.text


async def _forward_to_django(body: dict, settings: Settings) -> dict:
    """
    POST body nội bộ tới Django, kèm X-Internal-Token. Retry nhẹ (mặc định 2
    lần thêm, tổng 3 lần thử) khi lỗi mạng/timeout hoặc Django trả 5xx — để
    SePay không phải retry ngay lập tức khi lỗi chỉ là tạm thời phía Django.
    Lỗi 4xx từ Django coi là không tạm thời -> không retry. 400/404/409/422 (dữ liệu sai)
    -> HTTPException cùng mã; còn lại thất bại cuối cùng -> HTTPException 502.
    """
    url = f"{settings.django_internal_url.rstrip('/')}/api/internal/payments/sepay-webhook/"
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
            detail={"message": "Payload SePay không hợp lệ", "errors": exc.errors()},
        ) from exc

    if not is_incoming_transfer(payload):
        logger.info("Bỏ qua giao dịch không phải tiền vào: id=%s transferType=%s", payload.id, payload.transfer_type)
        return JSONResponse(status_code=200, content={"skipped": True, "reason": "not-incoming-transfer"})

    internal_payload = to_internal_payload(payload, settings.order_code_regex)
    django_result = await _forward_to_django(internal_payload.model_dump(mode="json"), settings)

    return JSONResponse(status_code=200, content=django_result)
