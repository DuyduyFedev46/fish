# Cổng thanh toán SePay: ghi chú triển khai (dev-notes)
> Cập nhật theo từng story khi làm xong. Mỗi agent thêm mục của mình, KHÔNG ghi đè mục
> của agent khác.

## P2 (adapter)
> BE (adapter) · 2026-09-26 · Story P2 "Adapter nhận IPN" — `02-stories.md`. Phạm vi:
> CHỈ `adapter/`, không đụng `backend/`.

### Việc đã làm
- Route mới `POST /ipn/sepay` (kênh CHÍNH V1) nhận IPN Cổng thanh toán SePay
  (`notification_type: ORDER_PAID | TRANSACTION_VOID`, `order{order_invoice_number,
  amount, currency, status,...}`, `transaction{...}`, `customer{...}`).
- Xác thực `X-Secret-Key` so hằng-thời-gian (`hmac.compare_digest`) với env
  `SEPAY_SECRET_KEY` (mới, bắt buộc).
- `ORDER_PAID` + `status=CAPTURED` + `currency=VND` -> map sang payload nội bộ
  `{bank_txn_id, order_code, amount, received_at, raw}` rồi gọi Django (xem "Contract nội
  bộ (GIẢ ĐỊNH)" bên dưới — **cần đối chiếu với agent làm P3**).
- `TRANSACTION_VOID` -> chỉ log cảnh báo (mã đơn + mã giao dịch, không có khoá), trả `200`,
  không đổi đơn/kho, không gọi Django (BR-TT-16).
- `status`/`currency` lạ ở `ORDER_PAID` -> chỉ log, trả `200`, không xác nhận, không gọi
  Django (Q9).
- `notification_type` khác 2 giá trị đã biết -> log cảnh báo, trả `200`, không gọi Django
  (an toàn khi SePay thêm loại thông báo mới).
- Payload hỏng vĩnh viễn (thiếu `order.order_invoice_number`, `order.amount`, hoặc mã giao
  dịch trong `transaction`) -> `400` (không `500`), log cảnh báo đủ để đối soát, log KHÔNG
  chứa khoá.
- Khoá sai/thiếu -> `401`, không gọi Django, không log giá trị khoá.
- Django lỗi mạng/timeout/5xx -> adapter **không** trả `200` (retry nhẹ rồi `502`, tái dùng
  cơ chế retry sẵn có của `/webhook/sepay`).
- Idempotent: adapter không tự chặn IPN gửi lại — dựa hoàn toàn vào Django chống trùng theo
  `bank_txn_id` (BR-TT-03). Có test chứng minh forward đủ 2 lần khi IPN gửi lại, không tự
  ý lọc phía adapter.
- Route webhook ngân hàng cũ `POST /webhook/sepay`: **tắt bằng cấu hình**
  (`SEPAY_BANK_WEBHOOK_ENABLED`, mặc định `false` — trả `404`, không xử lý, không gọi
  Django). Khi tắt, **không còn bắt buộc** `SEPAY_WEBHOOK_SECRET` lúc khởi động (trước đây
  bắt buộc luôn). Khi bật (`=true`), `SEPAY_WEBHOOK_SECRET` vẫn bắt buộc — fail-fast lúc
  khởi động Settings (`pydantic` `model_validator`) nếu thiếu. Đồng thời đổi so khoá route
  cũ (`Authorization: Apikey <secret>`) từ so chuỗi thường (`!=`) sang
  `hmac.compare_digest`.
- Log không chứa secret ở bất kỳ nhánh nào (đã test riêng cho cả 2 route).
- Thêm `adapter/Dockerfile`, `.dockerignore`, `.gcloudignore` (chưa có trước đây) để deploy
  Cloud Run `cangca-adapter` — theo mẫu `backend/Dockerfile`, dùng `uvicorn`, chỉ cài
  `requirements.txt` (không cài `requirements-dev.txt` vào image).
- Cập nhật `adapter/README.md` và `adapter/.env.example` (biến cấu hình mới, endpoint mới,
  giả định payload IPN).

### File đã sửa/thêm (chỉ `adapter/`)
- `adapter/app/config.py` — thêm `sepay_secret_key` (bắt buộc), `sepay_bank_webhook_enabled`
  (mặc định `false`), `sepay_webhook_secret` thành `Optional`, validator fail-fast.
- `adapter/app/schemas.py` — thêm `SePayIpnOrder`, `SePayIpnPayload`.
- `adapter/app/sepay.py` — thêm `pick_ipn_transaction_reference`,
  `strip_order_retry_suffix`, `is_ipn_order_paid`, `is_ipn_transaction_void`,
  `is_ipn_status_confirmable`, `to_internal_payload_from_ipn`, `IpnMalformedError`.
- `adapter/app/main.py` — thêm route `POST /ipn/sepay`, `_verify_sepay_ipn_secret`; sửa
  `/webhook/sepay` (kiểm cấu hình bật/tắt trước khi xác thực, so khoá bằng
  `hmac.compare_digest`); refactor `_forward_to_django` nhận `endpoint_path` để dùng chung
  cho cả 2 route.
- `adapter/tests/conftest.py` — thêm `SEPAY_SECRET_KEY`, `IPN_SECRET_HEADER`,
  `DJANGO_IPN_ENDPOINT`, `TEST_SETTINGS_DEFAULT` (+ fixture `client_default_config`) để test
  đúng cấu hình mặc định V1 (webhook cũ tắt), giữ `TEST_SETTINGS`/`client` cũ bật webhook để
  không phải sửa `tests/test_webhook.py`, `valid_sepay_ipn_payload`.
- `adapter/tests/test_ipn.py` — **mới**, 26 test cho `POST /ipn/sepay` + 2 test cho hành vi
  route cũ khi tắt (P2-AC8) + 1 test `/healthz` (trùng test cũ, giữ để rõ mã AC).
- `adapter/Dockerfile`, `adapter/.dockerignore`, `adapter/.gcloudignore` — mới.
- `adapter/README.md`, `adapter/.env.example` — cập nhật.

### Endpoint mới — `POST /ipn/sepay`
Request (header): `X-Secret-Key: <SEPAY_SECRET_KEY>`

Request (body mẫu, `ORDER_PAID`/CAPTURED/VND):
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
    "reference_code": "FT26092612345",
    "paid_at": "2026-09-26T10:15:00+07:00"
  },
  "customer": {"name": "Nguyen Van A", "phone": "0900000000"}
}
```

Response: `200` với nguyên body Django trả về (khi xác nhận), hoặc
`{"acknowledged": true, "action": "void_logged" | "ignored_unknown_type" |
"ignored_status_or_currency"}` (khi không gọi Django), hoặc `401`/`400`/`502` theo mô tả ở
trên. Xem chi tiết đầy đủ + ví dụ khác trong `adapter/README.md`.

### Migration
Không có (adapter không có DB/migration).

### Rule BR đã cài
BR-TT-02 (IPN qua adapter -> Django), BR-TT-03 (idempotent theo mã giao dịch, ưu tiên FT…),
BR-TT-12 (chỉ IPN đã xác thực mới xác nhận — chưa làm phần FE `success_url`, đó là P4),
BR-TT-13 (khoá không lộ, không log, không hard-code), BR-TT-16 (VOID không tự đổi
đơn/kho, chỉ log cảnh báo), BR-TT-15 (chỉ 1 kênh tự động bật ở V1 — route cũ tắt mặc
định), Q9 (status/currency lạ -> không tự xác nhận), Q5 (bóc hậu tố lần thử).

### Test
`cd adapter && .venv/bin/python -m pytest -q` → **67 passed, 0 failed** (41 test cũ +
26 test mới `test_ipn.py`, không sửa hành vi test cũ). Đã kiểm bằng cách cố tình xoá 1 dòng
log rồi chạy lại để chắc test log không rỗng-vô-nghĩa (test đỏ đúng lý do), sau đó khôi
phục lại — không phải trạng thái cuối cùng.

*Lưu ý cho điều phối viên:* nhiệm vụ giao có nhắc "mốc adapter 41 test" — đó trùng với số
test **đã có sẵn trước khi làm P2** (toàn bộ ở `test_webhook.py`, route cũ). Sau khi thêm
route `/ipn/sepay` theo đủ AC P2-AC1…AC9 (+ 1 test phòng thủ notification_type lạ ngoài
tài liệu), tổng số lên **67**. Không cắt bớt test để ép về đúng 41 — báo lại nếu ý muốn
thật sự là "41 test MỚI cho adapter" hay giới hạn nào khác.

### Còn nợ / giả định cần đối chiếu
1. **Contract nội bộ `POST /api/internal/payments/sepay-ipn/` là GIẢ ĐỊNH của agent
   adapter**, chưa đối chiếu được với agent làm story P3 (Django) vì lúc code P2,
   `backend/apps/sales/payments/internal_api.py` chưa có route/field nào cho IPN cổng
   (mới chỉ có `/api/internal/payments/sepay-webhook/` cũ, source duy nhất `WEBHOOK`).
   Quyết định của adapter: dùng **URL riêng** `/api/internal/payments/sepay-ipn/`, giữ
   NGUYÊN shape body `{bank_txn_id, order_code, amount, received_at, raw}` (đúng
   P2-AC1), để Django tự đặt `source` (vd `PaymentTransaction.Source.SEPAY_GATEWAY_IPN`)
   theo URL đã gọi, không cần thêm field `source`/`environment` vào body — Django biết
   môi trường (SANDBOX/PRODUCTION, BR-TT-14) qua cấu hình của chính nó (đã dùng để ký
   tham số ở story P1), không cần adapter gửi kèm.
   **Cần Duy/agent BE (Django) xác nhận hoặc đổi URL/shape này** trước khi coi P2+P3 khớp
   nhau; nếu đổi, chỉ cần sửa hằng số `DJANGO_IPN_ENDPOINT_PATH` trong `adapter/app/main.py`
   (và shape trong `to_internal_payload_from_ipn` nếu field đổi).
2. **Q4 (tên field `transaction` thật) vẫn ĐỎ** — chưa có payload sandbox thật. Adapter dò
   danh sách tên field ứng viên (`_IPN_REFERENCE_CODE_KEYS`, `_IPN_TRANSACTION_ID_KEYS`,
   `_IPN_TIMESTAMP_KEYS` trong `app/sepay.py`) — CHỈNH LẠI khi có payload sandbox thật
   (P6-AC5 "chạy thử đầu-cuối trên sandbox" sẽ lộ ra nếu sai).
3. **Q5 (hậu tố lần thử)**: định dạng hậu tố `-<số>` sau mã đơn `SO<yymmdd>-<6 hex>` là
   GIẢ ĐỊNH của adapter (`strip_order_retry_suffix`), vì P1 (Django, sinh tham số thanh
   toán) làm song song và chưa chốt định dạng thật lúc code P2. Kiểm lại khi P1 xong.
4. **`received_at` khi IPN không có field thời điểm nào adapter nhận diện được**: dùng thời
   điểm adapter NHẬN IPN (giờ VN) thay vì thời điểm SePay thu tiền thực tế — chấp nhận sai
   số nhỏ (độ trễ mạng), không coi là payload hỏng. Ghi rõ ở đây để không bất ngờ khi đối
   soát sao kê (ảnh hưởng BR-TT-06 "doanh thu ghi tại thời điểm xác nhận" — thời điểm xác
   nhận và thời điểm nhận IPN gần như trùng nhau trong thực tế nên tác động không đáng kể).
5. **Chưa deploy** (đúng phạm vi giao — không `gcloud`, không đụng production). `Dockerfile`
   mới thêm CHƯA được build/test thật (không có Docker trong môi trường làm việc); cấu trúc
   sao chép từ `backend/Dockerfile` (mẫu đã chạy production), rủi ro thấp nhưng cần P6 xác
   nhận build thành công trên Cloud Build trước khi tin tưởng hoàn toàn.
6. Route cũ `/webhook/sepay` khi TẮT trả `404` (không phải `403`) — chọn `404` để đúng tinh
   thần "route cũ không tồn tại/không xử lý"; nếu muốn phân biệt rõ "tắt do cấu hình" với
   "route thực sự không tồn tại" thì đổi sang `403`, không ảnh hưởng story nào khác (chưa có
   bên nào gọi route này ở V1).

---

## P5, P1, P3 (BE)
> BE (Django) · 2026-09-26 · Story P5 "Tổng đơn nguyên đồng", P1 "Lập tham số thanh toán
> cổng", P3 "Lõi ghi nhận giao dịch cổng" — `02-stories.md`. Phạm vi: CHỈ `backend/`.
>
> **Đối chiếu với P2 (adapter, đã xong khi tôi làm P3):** đã đọc mục "P2 (adapter)" ở trên +
> `adapter/app/main.py`/`app/sepay.py` thật (không chỉ theo dev-notes). Kết quả: dùng ĐÚNG
> path `POST /api/internal/payments/sepay-ipn/` (hằng số `DJANGO_IPN_ENDPOINT_PATH` ở
> adapter), ĐÚNG shape body `{bank_txn_id, order_code, amount, received_at, raw}` — KHÔNG
> cần thêm field `source`/`environment` vào body như adapter đã dự đoán đúng: Django tự biết
> nguồn (`Source.GATEWAY`, theo URL đã gọi) và môi trường (`settings.SEPAY_ENV`, cấu hình
> phía Django — cùng biến dùng để ký tham số ở P1). **Không cần đổi gì bên adapter.**

### P5 — Tổng đơn nguyên đồng (BR-BH-15, Q6)
- File sửa: `apps/sales/utils.py` (thêm `money_vnd` — làm tròn NGUYÊN ĐỒNG, half-up, biểu
  diễn lại 2 chữ số thập phân cho khớp cột DB); `apps/sales/orders/services.py`
  (`create_order`: `order.total_amount = money_vnd(total)` thay vì `_q(total)` — dòng đơn
  `SalesOrderLine.amount` GIỮ NGUYÊN 2 chữ số thập phân, không đổi).
- P5-AC3 (đơn cũ lẻ xu xin tham số thanh toán): **quyết định BE — làm tròn theo cùng quy tắc**
  khi lập tham số (`payments/checkout.py` gọi `money_vnd(order.total_amount)` lại một lần
  nữa phòng hờ), KHÔNG sửa ngược `order.total_amount` đã lưu (chứng từ không đổi ngược,
  bất biến #3/#8). Trong thực tế mọi đơn tạo SAU thay đổi này đã nguyên đồng sẵn — nhánh này
  chỉ là phòng thủ cho đơn tạo trước khi vá.
- Test: `apps/sales/orders/tests/test_p5_bh15_round_total.py` (2 test — lẻ xu đơn giản +
  có PricingRule %).
- Migration: KHÔNG (không đổi schema).

### P1 — Lập tham số thanh toán cổng (BR-TT-01, 13, 14, 17)
- File mới: `apps/sales/payments/checkout.py` (service — ký tham số, KHÔNG đụng
  `PaymentTransaction`), `apps/sales/payments/shop_api.py` (view Shop, `AllowAny`).
- Route mới: `POST /api/shop/orders/<order_code>/checkout/` (`config/api_urls.py`). KHÔNG
  cần 4 số cuối SĐT (khác tra đơn) vì response không chứa PII (P1-AC6).
- Settings mới (`config/settings.py`, đọc env — KHÔNG hard-code, BR-TT-14):
  `SEPAY_ENV` (mặc định `SANDBOX`), `SEPAY_MERCHANT_ID`, `SEPAY_SECRET_KEY`,
  `SEPAY_CHECKOUT_URL_SANDBOX` (mặc định `https://pay-sandbox.sepay.vn/v1/checkout/init`),
  `SEPAY_CHECKOUT_URL_PRODUCTION` (mặc định `https://pay.sepay.vn/v1/checkout/init`),
  `SHOP_BASE_URL` (mặc định `http://localhost:3000` — success/cancel/error_url trỏ về đây,
  BR-TT-12). Đã thêm tên biến (không giá trị thật) vào `backend/.env.example`.
- **Chữ ký + tên field: theo ĐÚNG SDK chính thức của SePay** (đọc trực tiếp mã nguồn
  `github.com/sepayvn/sepay-pg-node`, `src/checkout.ts` + `src/types.ts` — KHÔNG còn là giả
  định, đã sửa lại từ bản dựng đầu tiên):
  - Field checkout dùng tên `merchant` (KHÔNG phải `merchant_id`), thêm
    `operation="PURCHASE"`, `payment_method="BANK_TRANSFER"` (VietQR — BR-TT-01, V1 CHỈ dùng
    giá trị này), `order_description` (bắt buộc, không dấu — `"Thanh toan don <mã đơn>"`,
    hàm `_no_diacritics`/`_order_description`).
  - Chữ ký: duyệt field **THEO ĐÚNG THỨ TỰ CỦA FORM** (hằng `checkout.FIELD_ORDER`, khớp
    nguyên văn thứ tự trong SDK), bỏ qua key không có mặt hoặc giá trị `None`, mỗi field
    thành `"key=value"`, nối bằng `","` (`checkout._signature_string`) → HMAC-SHA256 rồi
    **BASE64** (KHÔNG phải hex — khác bản dựng đầu), khoá `SEPAY_SECRET_KEY`
    (`checkout._sign`).
  - Vì thứ tự quyết định chữ ký, `build_checkout_params` trả thêm `fields`: **mảng CÓ THỨ
    TỰ** `[{"name": .., "value": ..}, …]` (đã gồm `signature` ở cuối) — đây là **NGUỒN
    CHÍNH** để FE (P4) dựng form POST đúng thứ tự; các key top-level khác (`merchant`,
    `order_amount`, …) chỉ để tiện đọc/tương thích ngược, KHÔNG dùng để tự ráp lại form.
  - Test vector cố định (secret giả `"test-secret"`, tính độc lập bằng `hmac`+`base64` ngay
    trong test, không gọi lại hàm sản phẩm để tính "đáp án"): xem
    `SignatureAlgorithmVectorTests` — gồm cả test đổi thứ tự field → chữ ký khác, và test
    key `None` bị bỏ qua chứ không stringify thành `"None"`.
- **Q5 (hậu tố lần thử) — đã cài, khớp với adapter:** thêm field
  `SalesOrder.checkout_attempts` (PositiveIntegerField, default 0, có migration). Lần 1 gọi
  `checkout/` gửi đúng `order.code`; từ lần 2 (thanh toán lại) thêm hậu tố `-<n>` (n = số lần
  gọi, khoá dòng đơn bằng `select_for_update` khi tăng đếm — tránh 2 request đồng thời trùng
  hậu tố). Định dạng khớp CHÍNH XÁC regex adapter đã cài sẵn:
  `^(SO\d{6}-[0-9A-Za-z]{6})(?:-\d+)?$` (`strip_order_retry_suffix` — đã đọc trực tiếp
  `adapter/app/sepay.py` để đối chiếu, không chỉ theo mô tả).
- P1-AC7: `ShopOrderCreateView` (`apps/sales/orders/shop_api.py`) BỎ hẳn `_vietqr_stub` +
  key `"vietqr"` khỏi response đặt hàng. Đã sửa test cũ tham chiếu field này
  (`apps/sales/orders/tests/test_shop_api.py`).
- Test: `apps/sales/payments/tests/test_p1_sepay_checkout_params.py` (16 test — ký đúng
  + `fields` đúng thứ tự/nội dung, không lộ secret (kể cả trong `fields`), sandbox/production
  theo cấu hình, từ chối đơn hết hạn/đã huỷ/đã thanh toán/không tồn tại, thanh toán lại có
  hậu tố, không lộ PII, không còn `vietqr`, + 3 test vector thuật toán ký độc lập với sản
  phẩm — bao gồm test đổi thứ tự field ra chữ ký khác).
- Migration: `apps/sales/migrations/0006_salesorder_checkout_attempts.py` (thêm field,
  default 0 — an toàn với dữ liệu cũ).

### P3 — Lõi ghi nhận giao dịch cổng (BR-TT-02, 03, 10, 14, 15)
- Model (`apps/sales/models/payments.py`, migration
  `0005_paymenttransaction_duplicate_warning_and_more.py`):
  - `PaymentTransaction.Source` thêm `GATEWAY = "GATEWAY", "Cổng SePay"` (giữ nguyên
    `WEBHOOK`/`MANUAL` — dữ liệu cũ không đổi, AC9).
  - Thêm `PaymentTransaction.Environment` (`SANDBOX`/`PRODUCTION`) + field `environment`
    (blank mặc định "" — chỉ set khi `source=GATEWAY`, BR-TT-14).
  - Thêm field `duplicate_warning` (CharField, blank mặc định "") — nhãn nghi trùng UC-5.
- Service (`apps/sales/payments/services.py`):
  - `environment_for_source(source)`: `GATEWAY` → `settings.SEPAY_ENV` (upper), khác → `""`.
  - `_record_payment` (lõi dùng chung, TÁI DÙNG nguyên vẹn — không viết lại):
    set `environment=environment_for_source(source)` khi tạo `PaymentTransaction`; sau khi
    tạo dòng `OVERPAID` (nhánh "đơn đã xử lý, khoản này thành thừa"), nếu **nguồn mới ≠
    MANUAL** và tồn tại một khoản **MATCHED nguồn MANUAL cùng đơn, cùng số tiền** →
    gắn `duplicate_warning = DUPLICATE_MANUAL_WARNING` ("Nghi trùng xác nhận tay, đối chiếu
    sao kê trước khi hoàn", UC-5/BR-TT-15). `split_overpaid` (BR-TT-10, L8) TRUYỀN LẠI
    `environment` từ dòng gốc sang dòng `-THUA` tách ra.
  - Chống trùng (BR-TT-03/BR-TT-15 UC-5): KHÔNG viết thêm — cơ chế `bank_txn_id` unique có
    sẵn ở `_record_payment` đã tự lo cặp "Chủ xác nhận tay bằng FT… rồi IPN về SAU với ĐÚNG
    mã FT…" (P3-AC6, dedup trước khi tạo dòng mới). Chỉ cặp "IPN có mã KHÁC FT…" mới chạm
    nhánh `duplicate_warning` mới thêm ở trên (P3-AC7).
- API nội bộ (`apps/sales/payments/internal_api.py`, refactor không đổi hành vi cũ):
  - Tách `_parse_payment_body(d)` (validate chung) + `_handle_payment_ipn(request, *,
    source)` (lõi chung webhook cũ + IPN cổng mới) từ code cũ của
    `SepayWebhookInternalView` — **hành vi webhook cũ giữ nguyên 100%** (test cũ
    `test_internal_api.py` xanh không sửa).
  - View mới `SepayGatewayIpnInternalView` — `POST
    /api/internal/payments/sepay-ipn/` (route trong `config/api_urls.py`, đặt CẠNH route cũ
    `sepay-webhook/`), `source=PaymentTransaction.Source.GATEWAY`. Auth: cùng cơ chế
    `X-Internal-Token` + `hmac.compare_digest` như route cũ (`_token_ok`).
- Serializer/API hàng chờ (`apps/sales/payments/serializers.py`, `api.py`): thêm
  `environment`, `duplicate_warning` vào `PaymentTransactionSerializer` (để Chủ THẤY được
  trên hàng chờ, không chỉ nằm trong DB — P3-AC7 "hiện được"); thêm `source`, `environment`
  vào danh sách filter được của `PaymentTransactionViewSet` (BR-TT-14 "để lọc được"). KHÔNG
  thêm field giá vốn nào — permission/scope hàng chờ (chỉ `confirm_payment_manual`) không đổi.
- Test: `apps/sales/payments/tests/test_p3_sepay_gateway_ipn.py` (13 test — MATCHED nguồn
  GATEWAY + hoá đơn + phiếu giao PREPARING, sai token 401, ORPHAN sau tự huỷ, UNDERPAID,
  OVERPAID tách dòng `-THUA`, khoản cổng thứ 2 cho đơn đã trả → OVERPAID không nhãn (đối
  chứng AC7), IPN trùng mã FT với xác nhận tay → không ghi dòng mới, IPN khác mã FT cùng số
  tiền sau xác nhận tay → `duplicate_warning` (kiểm cả qua API `/api/sales/payments/{id}/`
  cho Chủ, không chỉ DB), môi trường SANDBOX/PRODUCTION theo cấu hình + xác nhận tay không
  có môi trường, migration không đổi dữ liệu cũ).
- Migration: `apps/sales/migrations/0005_paymenttransaction_duplicate_warning_and_more.py`
  (thêm 2 field + mở rộng choices `source`, KHÔNG đổi/xoá dữ liệu — an toàn với production).

### Contract JSON mẫu (khớp adapter, đã đối chiếu trực tiếp code P2)

**1) Shop lập tham số thanh toán — `POST /api/shop/orders/SO260926-A1B2C3/checkout/`**
Request: không cần body. Response `200` (tên field + thứ tự `fields` theo ĐÚNG SDK chính
thức SePay — `github.com/sepayvn/sepay-pg-node`, `src/checkout.ts`):
```json
{
  "gateway": "SEPAY",
  "environment": "SANDBOX",
  "checkout_url": "https://pay-sandbox.sepay.vn/v1/checkout/init",
  "fields": [
    {"name": "merchant", "value": "<SEPAY_MERCHANT_ID>"},
    {"name": "operation", "value": "PURCHASE"},
    {"name": "payment_method", "value": "BANK_TRANSFER"},
    {"name": "order_amount", "value": "540000"},
    {"name": "currency", "value": "VND"},
    {"name": "order_invoice_number", "value": "SO260926-A1B2C3"},
    {"name": "order_description", "value": "Thanh toan don SO260926-A1B2C3"},
    {"name": "success_url", "value": "https://<SHOP_BASE_URL>/shop/orders?code=SO260926-A1B2C3&result=success"},
    {"name": "error_url", "value": "https://<SHOP_BASE_URL>/shop/orders?code=SO260926-A1B2C3&result=error"},
    {"name": "cancel_url", "value": "https://<SHOP_BASE_URL>/shop/orders?code=SO260926-A1B2C3&result=cancel"},
    {"name": "signature", "value": "<base64 hmac-sha256, xem mục P1 ở trên>"}
  ],
  "merchant": "<SEPAY_MERCHANT_ID>",
  "operation": "PURCHASE",
  "payment_method": "BANK_TRANSFER",
  "order_invoice_number": "SO260926-A1B2C3",
  "order_amount": "540000",
  "currency": "VND",
  "order_description": "Thanh toan don SO260926-A1B2C3",
  "success_url": "https://<SHOP_BASE_URL>/shop/orders?code=SO260926-A1B2C3&result=success",
  "cancel_url": "https://<SHOP_BASE_URL>/shop/orders?code=SO260926-A1B2C3&result=cancel",
  "error_url": "https://<SHOP_BASE_URL>/shop/orders?code=SO260926-A1B2C3&result=error",
  "signature": "<base64 hmac-sha256, xem mục P1 ở trên>"
}
```
`fields` là NGUỒN CHÍNH để FE (P4) dựng form POST (đúng thứ tự, gồm cả `signature` ở cuối);
các key top-level còn lại chỉ để tiện đọc/tương thích ngược.
Lần gọi thứ 2 trở đi cho CÙNG đơn (thanh toán lại): `order_invoice_number` =
`"SO260926-A1B2C3-2"`, `-3`, … (adapter tự bóc lại `"SO260926-A1B2C3"` bằng
`strip_order_retry_suffix` khi khớp đơn — KHÔNG cần Shop FE làm gì thêm).
Lỗi: `404 {"detail": "Không tìm thấy đơn."}` (mã đơn sai); `400 {"detail": "Đơn đã hết hạn
giữ hàng, vui lòng đặt lại.", "code": "BR-TT-17"}` hoặc `400 {"detail": "Đơn đã thanh
toán.", "code": "BR-TT-17"}`.

**2) Adapter → Django (P2 gọi P3) — `POST /api/internal/payments/sepay-ipn/`**
Header: `X-Internal-Token: <INTERNAL_SERVICE_TOKEN>` (cùng giá trị adapter/Django).
Request (adapter gửi, `to_internal_payload_from_ipn` — đã đọc code thật, không phải suy
đoán):
```json
{
  "bank_txn_id": "FT26092612345",
  "order_code": "SO260926-A1B2C3",
  "amount": 540000,
  "received_at": "2026-09-26T10:15:00+07:00",
  "raw": { "...": "nguyên payload IPN gốc, KHÔNG có header X-Secret-Key" }
}
```
Response `200` khi khớp đủ:
```json
{"matched": true, "order_status": "PROCESSING", "match_status": "MATCHED"}
```
`PaymentTransaction` ghi được: `source="GATEWAY"`, `environment="SANDBOX"` (theo
`SEPAY_ENV` LÚC NHẬN IPN — Django tự gắn, adapter không cần gửi field này).
Response khi thiếu tiền: `{"matched": false, "order_status": "BOOKED", "match_status":
"UNDERPAID"}`. Khi không khớp đơn nào: `{"matched": false, "order_status": null}`
(`match_status="UNMATCHED"`, vào hàng chờ Chủ). Sai/thiếu token: `401`. Payload thiếu field
bắt buộc: `400 {"detail": "...", "code": "WEBHOOK_INVALID_INPUT"}`.

**3) Hàng chờ Chủ xem — `GET /api/sales/payments/{id}/`** (trích field mới P3):
```json
{
  "id": 42,
  "bank_txn_id": "SPG-NOFT",
  "amount": "540000",
  "source": "GATEWAY",
  "source_label": "Cổng SePay",
  "environment": "SANDBOX",
  "duplicate_warning": "Nghi trùng xác nhận tay, đối chiếu sao kê trước khi hoàn",
  "match_status": "OVERPAID",
  "resolution_status": "OPEN"
}
```

### Rule BR đã cài
BR-BH-15 (P5, tổng đơn nguyên đồng half-up), BR-TT-01 (bỏ `vietqr` giả), BR-TT-13 (khoá
không lộ — response/log không chứa `SEPAY_SECRET_KEY`), BR-TT-14 (URL/khoá/môi trường theo
cấu hình; môi trường ghi kèm giao dịch cổng), BR-TT-17 (chỉ lập tham số cho đơn Giữ chỗ còn
TTL), BR-TT-02/03 (IPN qua adapter, idempotent theo `bank_txn_id`, TÁI DÙNG
`_record_payment`), BR-TT-10 (OVERPAID tách dòng `-THUA`, môi trường truyền theo dòng gốc),
BR-TT-15 (nhãn nghi trùng xác nhận tay + IPN muộn khác mã).

### Test
`cd backend && .venv/bin/python manage.py test` → **578 passed, 0 failed** (547 mốc giao +
2 P5 + 16 P1 + 13 P3). `manage.py makemigrations --check --dry-run` → sạch (không sinh gì
mới ngoài 2 migration đã tạo và commit vào code). Đã kiểm TDD thật (không phải test vô
nghĩa): cố tình tắt logic `duplicate_warning` và logic hậu tố lần thử, chạy lại thấy đúng
test liên quan đỏ đúng lý do, rồi khôi phục lại code thật trước khi báo cáo.

### Còn nợ / giả định cần đối chiếu (BE)
1. **Chuỗi ký + tên field (P1) đã sửa theo SDK chính thức** `sepayvn/sepay-pg-node`
   (`src/checkout.ts`, `src/types.ts` — đọc trực tiếp mã nguồn theo yêu cầu điều phối viên,
   KHÔNG còn là giả định thuần). Vẫn còn 1 điểm CHƯA kiểm được vì không có tài khoản
   sandbox thật trong phiên: **`env` có cần gửi làm field hay không** — SDK hỗ trợ key `env`
   trong `FIELD_ORDER` nhưng V1 KHÔNG gửi (chọn môi trường qua `checkout_url` sandbox/
   production, không qua field `env`); nếu SDK/PGAPI thực ra BẮT BUỘC field `env` thì chỉ
   cần thêm 1 dòng `"env": environment.lower()` (hoặc giá trị đúng SDK) vào `values` trong
   `build_checkout_params` — không ảnh hưởng chỗ khác vì `FIELD_ORDER`/`_signature_string`
   đã có sẵn vị trí cho `env`. Kiểm lại ở P6 (chạy thử sandbox thật).
2. **Q5 hậu tố lần thử**: đã cài xong VÀ khớp adapter (`strip_order_retry_suffix`), nhưng
   CHƯA kiểm được trên sandbox thật liệu SePay có thực sự từ chối tái sử dụng
   `order_invoice_number` hay không (tiền đề của cả Q5). Nếu sandbox chấp nhận dùng lại y
   nguyên mã cũ thì hậu tố này vô hại (adapter vẫn bóc đúng), chỉ là dư thừa.
2b. `SalesOrder.checkout_attempts` tăng mỗi lần GỌI thành công (kể cả khi khách không bao
   giờ hoàn tất thanh toán ở lần đó) — nghĩa là "lần thử" đếm theo số lần bấm nút, không
   phải số lần thực sự tới trang SePay. Chấp nhận được vì hậu tố chỉ cần DUY NHẤT, không
   cần đúng "lần thứ mấy" về mặt hiển thị.
3. **`SHOP_BASE_URL` mặc định `http://localhost:3000`** — Duy/vận hành cần đặt biến môi
   trường thật (domain Firebase `cangca-loc`) trước khi deploy production; sandbox test nội
   bộ dùng giá trị nào cũng được vì Shop CHƯA mở công khai (Q3).
4. **Phí giao dịch cổng SePay**: không hạch toán (ngoài phạm vi P5/P1/P3, xem Q12 ở
   `01-analysis.md`).
5. **success_url/cancel_url/error_url dùng chung 1 trang, khác nhau qua `?result=`** — P4
   (FE Shop) tự quyết định có dùng query này để hiển thị khác nhau hay không; BE chỉ đảm bảo
   BR-TT-12 (không tự suy ra "đã thanh toán" từ việc quay về `success_url`).
