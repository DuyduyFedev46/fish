# Adapter FastAPI — Cảng Cá Lộc

Lớp adapter **mỏng**, KHÔNG đụng DB/ORM. Nhận thông báo thanh toán của SePay (bên thứ 3),
validate/transform payload, rồi gọi API nội bộ Django. Idempotency theo mã giao dịch do
Django lo (`sales.confirm_payment`) — adapter chỉ forward.

**V1 (hồ sơ `doc/features/2026-09-26-sepay-cong-thanh-toan`, quyết định Duy 2026-09-26):
kênh CHÍNH là IPN Cổng thanh toán (`POST /ipn/sepay`)`.** Route webhook biến động số dư CŨ
(`POST /webhook/sepay`) **giữ code nhưng TẮT mặc định** — bật lại bằng cấu hình
`SEPAY_BANK_WEBHOOK_ENABLED=true` nếu cần dùng song song (xem BR-TT-15 về chống trùng khi
bật cả hai kênh).

Xem hợp đồng gốc: `../doc/BUILD-PLAN.md` (Contract B mục "API cho adapter",
Contract C), `../doc/decisions.md` (quyết định 2026-09-09 Django/FastAPI),
`../doc/ecosystem-l1.md` mục 3 và 6, `../doc/features/2026-09-26-sepay-cong-thanh-toan/`
(phân tích + story P2 + `03-dev-notes.md` mục "P2 (adapter)").

## Cấu trúc

```
adapter/
  app/
    main.py      # FastAPI app: routes /healthz, /webhook/sepay (cũ, tắt mặc định), /ipn/sepay (chính, V1)
    config.py    # Settings (pydantic-settings, đọc env/.env)
    schemas.py   # Pydantic models: payload SePay/IPN vào, payload nội bộ ra
    sepay.py     # Transform payload SePay/IPN -> body nội bộ Django (không state)
  tests/
    conftest.py
    test_webhook.py   # route /webhook/sepay (cũ)
    test_ipn.py        # route /ipn/sepay (chính, V1)
  Dockerfile              # build image Cloud Run (cangca-adapter)
  .dockerignore
  .gcloudignore
  requirements.txt       # deps runtime
  requirements-dev.txt   # + pytest, respx (chỉ để test)
  .env.example
  pytest.ini
```

## Endpoint

- `GET /healthz` -> `{"status": "ok"}`

### `POST /ipn/sepay` (chính, V1) — IPN Cổng thanh toán SePay

Nhận IPN theo tài liệu SePay Cổng thanh toán
(https://developer.sepay.vn/vi/cong-thanh-toan/IPN — xem GIẢ ĐỊNH về tên field trong
docstring `app/schemas.py:SePayIpnPayload`, Q4 trong hồ sơ tính năng vẫn ĐỎ vì chưa có
payload sandbox thật lúc code).

- Xác thực: header `X-Secret-Key: <SEPAY_SECRET_KEY>`, so hằng-thời-gian
  (`hmac.compare_digest`). Thiếu/sai -> `401`, KHÔNG gọi Django, log KHÔNG chứa khoá.
- `notification_type = "TRANSACTION_VOID"` -> `200`, chỉ log cảnh báo (mã đơn + mã giao
  dịch), **không** đổi đơn/kho, **không** gọi Django (BR-TT-16 — V1 chỉ VietQR nên gần như
  không xảy ra; bật thẻ sau này phải nâng thành cảnh báo trên ERP).
- `notification_type = "ORDER_PAID"`:
  - `order.status = "CAPTURED"` và `order.currency = "VND"` -> map sang payload nội bộ
    `{bank_txn_id, order_code, amount, received_at, raw}` rồi
    `POST {DJANGO_INTERNAL_URL}/api/internal/payments/sepay-ipn/` kèm
    `X-Internal-Token: <INTERNAL_SERVICE_TOKEN>`, trả nguyên kết quả Django, `200`.
    - `bank_txn_id`: ưu tiên mã tham chiếu ngân hàng (FT…) trong `transaction` nếu có
      (đúng mã Chủ gõ khi xác nhận tay, BR-TT-03/Q4), lùi về id giao dịch SePay.
    - `order_code`: `order.order_invoice_number`, bóc hậu tố lần thử nếu có (Q5, thanh
      toán lại cùng đơn — xem `app/sepay.py:strip_order_retry_suffix`).
  - `status`/`currency` khác -> **không** xác nhận đơn, chỉ log để Chủ xem, **không** gọi
    Django, trả `200` (Q9).
  - `notification_type` khác 2 giá trị trên -> log cảnh báo, `200`, không gọi Django (an
    toàn khi SePay thêm loại thông báo mới, không tự treo/không tự xác nhận).
- Payload hỏng vĩnh viễn (thiếu `order.order_invoice_number`, `order.amount`, hoặc mã giao
  dịch trong `transaction`) -> `400` (KHÔNG `500`), log cảnh báo đủ để đối soát (mã đơn +
  mã giao dịch nếu có), không log khoá (E9).
- Django lỗi mạng/timeout/5xx -> **không** trả `200` (retry nhẹ rồi `502`, để SePay gửi
  lại — dùng chung cơ chế retry với `/webhook/sepay`).
- Idempotent theo `bank_txn_id`: **Django** chống trùng (`sales.confirm_payment`); adapter
  không tự chặn IPN gửi lại — chỉ forward, Django trả đúng kết quả đã ghi (BR-TT-03).

**Contract nội bộ `/api/internal/payments/sepay-ipn/` là GIẢ ĐỊNH của agent adapter** (chưa
có `03-dev-notes.md` phía Django lúc code — story P2/P3 làm song song). Chọn URL riêng với
`/api/internal/payments/sepay-webhook/` (không thêm field `source` vào body) để Django phân
biệt nguồn "Cổng SePay" (BR-TT-15/P3-AC1) ngay từ route. Đối chiếu lại với agent làm P3, xem
`../doc/features/2026-09-26-sepay-cong-thanh-toan/03-dev-notes.md` mục "P2 (adapter)".

### `POST /webhook/sepay` (cũ, TẮT mặc định V1) — webhook biến động số dư ngân hàng

Mặc định `SEPAY_BANK_WEBHOOK_ENABLED=false`: route trả `404`, không xử lý, không gọi
Django, và **không** bắt buộc cấu hình `SEPAY_WEBHOOK_SECRET` lúc khởi động. Bật lại
(`SEPAY_BANK_WEBHOOK_ENABLED=true`) thì `SEPAY_WEBHOOK_SECRET` bắt buộc (adapter từ chối
khởi động nếu thiếu), và hành vi dưới đây giữ nguyên như trước:

- nhận payload SePay, forward Django:
  - Xác thực: header `Authorization: Apikey <SEPAY_WEBHOOK_SECRET>`
    (thiếu/sai -> `401`).
  - Payload không đúng dạng SePay (thiếu field bắt buộc, sai kiểu, số tiền
    <= 0 / dưới 1đ sau làm tròn 0,01 (L8, BR-TT-08) / NaN / Infinity, `transactionDate` không parse được, ...) -> `400`
    `{"detail": {"message": "Payload SePay không hợp lệ", "errors": [{"type", "loc", "msg"}]}}`
    (QA · B7: trước đây ra 500 vì `errors()` chứa `ValueError`/`Decimal` không JSON được;
    nay bỏ `ctx`/`input`/`url`). Không forward Django.
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
| `SEPAY_SECRET_KEY` | có | Secret xác thực IPN Cổng thanh toán (`X-Secret-Key`, kênh chính V1) |
| `SEPAY_BANK_WEBHOOK_ENABLED` | không (mặc định `false`) | Bật route cũ `/webhook/sepay` (webhook biến động số dư). V1 để tắt |
| `SEPAY_WEBHOOK_SECRET` | chỉ khi `SEPAY_BANK_WEBHOOK_ENABLED=true` | Secret so khớp header `Authorization: Apikey <secret>` từ webhook cũ |
| `ORDER_CODE_REGEX` | không | Regex dự phòng rút mã đơn từ nội dung CK cho webhook cũ (mặc định `[A-Z]{1,4}[0-9]{4,}`) |
| `DJANGO_REQUEST_TIMEOUT_SECONDS` | không | Timeout gọi Django (mặc định 10s) |
| `DJANGO_REQUEST_RETRIES` | không | Số lần thử lại thêm khi lỗi (mặc định 2) |

Khởi động thất bại (fail-fast) nếu `SEPAY_BANK_WEBHOOK_ENABLED=true` mà thiếu
`SEPAY_WEBHOOK_SECRET` — tránh route cũ chạy "câm" (bật nhưng không ai xác thực được).

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
chạy.

- `tests/test_webhook.py` (route cũ `/webhook/sepay`, bật cấu hình để test): webhook hợp lệ
  forward đúng shape + header; fallback rút order_code bằng regex khi SePay không tự nhận
  diện được `code`; sai/thiếu secret -> 401; payload rác / body không phải JSON -> 400;
  Django trả 5xx hoặc lỗi mạng -> 502 (có retry nhẹ); Django 400 -> 400 không retry,
  401 -> 502; `bank_txn_id` = referenceCode chuẩn hoá, lùi về `id`; giao dịch `out` bị bỏ
  qua không forward.
- `tests/test_ipn.py` (route chính `/ipn/sepay`, V1): IPN `ORDER_PAID`+CAPTURED+VND forward
  đúng shape (kể cả bóc hậu tố lần thử, lùi transaction id khi thiếu reference code); sai/
  thiếu `X-Secret-Key` -> 401 không gọi Django, log không chứa khoá; gửi lại IPN 2 lần ->
  forward cả 2 lần (idempotent là việc của Django); Django 5xx/mất mạng -> không trả 200;
  payload hỏng (thiếu mã đơn/số tiền/mã giao dịch) -> 400 không 500, log không chứa khoá;
  `status`/`currency` lạ -> 200 không gọi Django, có log; `TRANSACTION_VOID` -> 200 không
  gọi Django, có log cảnh báo không chứa khoá; route cũ tắt mặc định -> từ chối, khởi động
  không đòi `SEPAY_WEBHOOK_SECRET`; bật cấu hình mà thiếu secret -> khởi động thất bại.

## Giả định về IPN Cổng thanh toán (ghi rõ vì Q4 trong hồ sơ tính năng vẫn ĐỎ)

Payload tham khảo tóm tắt tài liệu SePay
(https://developer.sepay.vn/vi/cong-thanh-toan/IPN — không có tài khoản Cổng thanh toán
thật để đối chiếu 1:1 lúc build, xem `01-analysis.md` mục "Nguồn kỹ thuật SePay"):

```json
{
  "notification_type": "ORDER_PAID",
  "order": {
    "order_invoice_number": "SO260926-A1B2C3",
    "amount": 540000,
    "currency": "VND",
    "status": "CAPTURED"
  },
  "transaction": {
    "id": 999888,
    "reference_code": "FT26092612345"
  },
  "customer": {"...": "..."}
}
```

- Tên field con trong `transaction` (mã tham chiếu ngân hàng FT…) CHƯA CHẮC đúng 100% —
  adapter dò một danh sách tên field ứng viên theo thứ tự ưu tiên, xem
  `app/sepay.py:pick_ipn_transaction_reference` (`_IPN_REFERENCE_CODE_KEYS`,
  `_IPN_TRANSACTION_ID_KEYS`). Chỉnh danh sách này khi có payload sandbox thật.
- `received_at`: dò một số tên field thời điểm giao dịch trong `transaction`
  (`_IPN_TIMESTAMP_KEYS`); không có field nào parse được thì dùng thời điểm adapter nhận
  IPN (giờ VN, `UTC+7`) — KHÔNG coi là payload hỏng.
- Hậu tố lần thử khi thanh toán lại (Q5, `order_invoice_number` dạng
  `SO<yymmdd>-<6 ký tự hex>[-<số lần thử>]`): xem `app/sepay.py:strip_order_retry_suffix`.
  Định dạng hậu tố thật do BE (story P1) chọn — kiểm lại khi P1 xong.
- Endpoint Django `POST /api/internal/payments/sepay-ipn/` (body
  `{bank_txn_id, order_code, amount, received_at, raw}`) là **GIẢ ĐỊNH của agent adapter**
  — chưa đối chiếu được với agent làm story P3 (Django) lúc code song song. Xem
  `03-dev-notes.md` mục "P2 (adapter)" trong hồ sơ tính năng.

## Giả định về payload webhook SePay cũ (biến động số dư — route TẮT mặc định V1)

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
