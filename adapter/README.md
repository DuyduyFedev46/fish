# Adapter FastAPI — Cảng Cá Lộc

Lớp adapter **mỏng**, KHÔNG đụng DB/ORM. Chỉ nhận webhook SePay (bên thứ 3),
validate/transform payload, rồi gọi API nội bộ Django
(`/api/internal/payments/sepay-webhook/`). Idempotency theo `bank_txn_id` do
Django lo (`sales.confirm_payment`) — adapter chỉ forward.

Xem hợp đồng gốc: `../doc/BUILD-PLAN.md` (Contract B mục "API cho adapter",
Contract C), `../doc/decisions.md` (quyết định 2026-09-09 Django/FastAPI),
`../doc/ecosystem-l1.md` mục 3 và 6.

## Cấu trúc

```
adapter/
  app/
    main.py      # FastAPI app: routes /healthz, /webhook/sepay
    config.py    # Settings (pydantic-settings, đọc env/.env)
    schemas.py   # Pydantic models: payload SePay vào, payload nội bộ ra
    sepay.py     # Transform payload SePay -> body nội bộ Django (không state)
  tests/
    conftest.py
    test_webhook.py
  requirements.txt       # deps runtime
  requirements-dev.txt   # + pytest, respx (chỉ để test)
  .env.example
  pytest.ini
```

## Endpoint

- `GET /healthz` -> `{"status": "ok"}`
- `POST /webhook/sepay` — nhận payload SePay, forward Django:
  - Xác thực: header `Authorization: Apikey <SEPAY_WEBHOOK_SECRET>`
    (thiếu/sai -> `401`).
  - Payload không đúng dạng SePay (thiếu field bắt buộc, sai kiểu, số tiền
    <= 0, ...) -> `400`.
  - Giao dịch `transferType != "in"` (không phải tiền vào) -> bỏ qua, trả
    `200 {"skipped": true, "reason": "not-incoming-transfer"}`, KHÔNG forward
    Django (đây là housekeeping của webhook, không phải business rule).
  - Giao dịch hợp lệ -> transform sang
    `{bank_txn_id, order_code, amount, received_at, raw:{...}}` rồi
    `POST {DJANGO_INTERNAL_URL}/api/internal/payments/sepay-webhook/` kèm
    header `X-Internal-Token: <INTERNAL_SERVICE_TOKEN>`. Trả về nguyên body
    Django phản hồi, status `200`.
  - Django lỗi mạng/timeout hoặc trả 5xx -> thử lại nhẹ (mặc định 2 lần,
    cấu hình qua `DJANGO_REQUEST_RETRIES`) rồi mới trả `502` (để SePay gửi
    lại webhook). Django trả 4xx -> lỗi không tạm thời, không retry:
    400/404/409/422 (dữ liệu sai, vd số tiền ngoài miền) -> trả lại đúng mã đó
    kèm body Django trong `detail` để SePay không gửi lại mãi (QA L7 · B13);
    401/403 (token nội bộ sai = cấu hình phía mình) -> `502`.

## Cấu hình (env / `.env`)

Copy `.env.example` thành `.env` rồi điền giá trị thật:

| Biến | Bắt buộc | Ý nghĩa |
|---|---|---|
| `DJANGO_INTERNAL_URL` | có | Base URL Django nội bộ |
| `INTERNAL_SERVICE_TOKEN` | có | Giá trị header `X-Internal-Token` khi gọi Django |
| `SEPAY_WEBHOOK_SECRET` | có | Secret so khớp header `Authorization: Apikey <secret>` từ SePay |
| `ORDER_CODE_REGEX` | không | Regex dự phòng rút mã đơn từ nội dung CK (mặc định `[A-Z]{1,4}[0-9]{4,}`) |
| `DJANGO_REQUEST_TIMEOUT_SECONDS` | không | Timeout gọi Django (mặc định 10s) |
| `DJANGO_REQUEST_RETRIES` | không | Số lần thử lại thêm khi lỗi (mặc định 2) |

## Cách chạy

```bash
cd adapter
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # rồi sửa giá trị thật
uvicorn app.main:app --port 9000
```

## Cách test

```bash
cd adapter
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest      # hoặc: python -m pytest -v
```

Test dùng `respx` để mock lời gọi `httpx` sang Django — không cần Django thật
chạy. Bao gồm: webhook hợp lệ forward đúng shape + header; fallback rút
order_code bằng regex khi SePay không tự nhận diện được `code`; sai/thiếu
secret -> 401; payload rác / body không phải JSON -> 400; Django trả 5xx hoặc
lỗi mạng -> 502 (có retry nhẹ); Django 400 -> 400 không retry, 401 -> 502;
`bank_txn_id` = referenceCode chuẩn hoá, lùi về `id`; giao dịch `out` bị bỏ qua
không forward.

## Giả định về payload SePay (ghi rõ vì không có tài khoản SePay thật để đối chiếu)

Payload tham khảo từ tài liệu công khai của SePay
(https://docs.sepay.vn/tich-hop-webhooks.html — mục Payload):

```json
{
  "id": 92704,
  "gateway": "Vietcombank",
  "transactionDate": "2024-07-02 11:08:33",
  "accountNumber": "1017588888",
  "subAccount": "",
  "code": "SEVN63DC8E5C",
  "content": "SEVN63DC8E5C chuyen tien",
  "transferType": "in",
  "description": "NGUYEN VAN A chuyen tien",
  "transferAmount": 5000000,
  "accumulated": 105000000,
  "referenceCode": "FT24012345678"
}
```

- `bank_txn_id` = `referenceCode` (mã FT… ngân hàng, in trên sao kê — chính mã
  Chủ gõ khi xác nhận tay) đã chuẩn hoá: bỏ mọi khoảng trắng, viết hoa (giống
  hệt `normalize_bank_txn_id` bên Django). Lùi về `str(id)` chỉ khi
  `referenceCode` trống. `id` SePay luôn nằm trong `raw` (QA L7 · B12).
- `order_code`: ưu tiên field `code` — giả định Lộc cấu hình sẵn trên
  dashboard SePay (mục Cấu hình chung) một tiền tố/mã hoá đơn để SePay tự
  nhận diện mã đơn hàng trong nội dung chuyển khoản và trả về ở field này
  (đúng cơ chế SePay công bố — xem ví dụ trên, SePay tự nhận diện
  `SEVN63DC8E5C` từ `content`). Nếu Lộc CHƯA cấu hình (`code` rỗng/null),
  adapter fallback dò bằng regex `ORDER_CODE_REGEX` trong `content` rồi
  `description`. **Format `order_code` thật (vd `DH000123`) do Agent A
  (sales) chốt sau — chỉnh `ORDER_CODE_REGEX` khi có format chính thức.**
  Nếu không tìm được order_code, adapter vẫn forward Django với
  `order_code=""` thay vì tự chặn — khớp không được là ca nghiệp vụ hợp lệ
  ("thanh toán mồ côi", BR-TT-05), không phải lỗi request.
- Xác thực webhook bằng HEADER `Authorization: Apikey <SEPAY_WEBHOOK_SECRET>`
  — đây là 1 trong 4 phương thức SePay hỗ trợ cấu hình trên dashboard
  (HMAC-SHA256 / API Key / OAuth2 / không xác thực). Chọn header vì tách
  biệt khỏi business payload, validate được độc lập trước khi đụng tới body.
- Chỉ forward giao dịch `transferType == "in"` (tiền vào); `"out"` bị bỏ qua
  ngay tại adapter.
- `transactionDate` dạng `"YYYY-MM-DD HH:MM:SS"` (giờ VN, không timezone) —
  adapter parse rồi chuẩn hoá về ISO 8601 trước khi gửi Django.
