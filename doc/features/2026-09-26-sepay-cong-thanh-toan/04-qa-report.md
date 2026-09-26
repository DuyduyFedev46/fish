# QA — Cổng thanh toán SePay (VietQR) · lần 1 · 2026-09-26

## Kết luận: APPROVED — mọi AC của P1, P2, P3, P4, P5 pass qua kiểm chứng sống (không mock) + hồi quy toàn bộ backend/adapter/frontend/erp-console xanh; không phát hiện lỗi Critical/High/Medium chặn.

## Tổng: 96 ca (trực tiếp QA lần này, không tính lại 582 test backend + 67 test adapter có sẵn) · ✅ 96 · ❌ 0 · ⏸ 0

Phạm vi lần này: P1, P2, P3, P4, P5 (đúng như điều phối viên giao). P6 (deploy) và P8 (ERP)
**chưa triển khai** — không có gì để QA. P7 (tài liệu) là việc của BA/Duy, không kiểm bằng
test tự động.

## Môi trường QA đã dựng (tại máy, không gọi SePay thật)
- Django `manage.py runserver 127.0.0.1:8123`, DB SQLite tạm riêng trong scratchpad
  (`qa_db.sqlite3`, KHÔNG đụng `backend/db.sqlite3`), `migrate` + `bootstrap_masterdata` +
  `seed_demo`, thêm `CORS_ALLOWED_ORIGINS=http://localhost:3410` (thiếu ban đầu → Shop bị
  chặn CORS, xem mục "Lỗi môi trường" bên dưới, đã tự sửa bằng env, không sửa code).
- Adapter `uvicorn app.main:app` port 8199, `SEPAY_SECRET_KEY=test-secret`,
  `INTERNAL_SERVICE_TOKEN` khớp Django, `SEPAY_BANK_WEBHOOK_ENABLED=false` (mặc định V1).
- Frontend Shop build thật (`NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=http://localhost:8123
  npm run build`), serve bằng `firebase serve --only hosting --port 3410` (tôn trọng
  `trailingSlash`/`cleanUrls` của `firebase.json` — cần vì `success_url`/`cancel_url`/
  `error_url` do BE sinh không có `/` cuối trước query string).
- 4 user QA (`qa_chu/qa_qly/qa_kho/qa_giao`, mỗi user 1 Group) + token DRF để kiểm phân quyền.
- 1 mặt hàng QA tự tạo (`QA-ROUND`, giá 150.500đ/kg, batch 50kg) để tái hiện đúng ví dụ lẻ
  xu 0,125kg trong hồ sơ (18.812,50đ) — dữ liệu test, không đụng code sản phẩm.
- Test IPN bằng giả lập JSON đúng cấu trúc tài liệu SePay (không gọi SePay thật, không có
  sandbox IPN thật — đúng giới hạn được giao).

## Theo AC

### P1 — Lập tham số thanh toán cổng (BE)
| Mã | Kết quả | Bằng chứng |
|---|---|---|
| P1-AC1 | ✅ | `POST /checkout/` trả đủ field đúng thứ tự; **tự tính lại chữ ký HMAC-SHA256 base64 độc lập bằng secret `test-secret`** → khớp byte-for-byte `Tfl2aIDf9MtZoWbuXeM4dCA5kyLOrVSQGt6JUQQxiKE=` |
| P1-AC2 | ✅ | `grep` response + `django.log` không có `test-secret`/`SEPAY_SECRET_KEY` |
| P1-AC3 | ✅ | `SEPAY_ENV=SANDBOX` → `checkout_url=pay-sandbox.sepay.vn`; đổi env, restart Django (không sửa code) → `SEPAY_ENV=PRODUCTION` → `checkout_url=pay.sepay.vn`, `environment=PRODUCTION` |
| P1-AC4 | ✅ | 4 trạng thái đều đúng message/mã: `AUTO_CANCELLED` → 400 "Đơn đã hết hạn giữ hàng…"; `PROCESSING` (đã trả) → 400 "Đơn đã thanh toán."; `BOOKED` nhưng `booked_expires_at` quá khứ → 400 hết hạn; mã đơn không tồn tại → 404 "Không tìm thấy đơn." |
| P1-AC5 | ✅ | Gọi `checkout/` 3 lần liên tiếp cho cùng đơn → `order_invoice_number` = gốc, `-2`, `-3`; `order_amount` không đổi qua các lần |
| P1-AC6 | ✅ | Response `checkout/` và `orders/` (đặt hàng) không có `name`/`phone`/`delivery_address` |
| P1-AC7 | ✅ | Response `POST /api/shop/orders/` không còn key `vietqr` |

### P2 — Adapter nhận IPN
| Mã | Kết quả | Bằng chứng |
|---|---|---|
| P2-AC1 | ✅ | IPN hợp lệ → Django nhận đúng shape `{bank_txn_id, order_code, amount, received_at, raw}`; đơn chuyển `PROCESSING`, adapter trả 200 |
| P2-AC2 | ✅ | Sai khoá → 401 `{"detail":"Sai hoặc thiếu X-Secret-Key"}`; thiếu khoá → 401 tương tự; `grep adapter.log` không có `test-secret` |
| P2-AC3 | ✅ | Gửi lại y hệt IPN đã xử lý → vẫn 200, **1** hoá đơn, **1** dòng `PaymentTransaction` (đếm lại bằng DB) |
| P2-AC4 | ✅ | Kill Django, gửi IPN → adapter trả **502** (không 200), message nêu rõ lỗi mạng |
| P2-AC5 | ✅ | Thiếu `order.amount` → 400 `{"detail":"Thiếu order.amount."}` |
| P2-AC6 | ✅ | `status=PENDING` → 200 `ignored_status_or_currency`, không tạo `PaymentTransaction`; `currency=USD` → 200 `ignored_status_or_currency` tương tự |
| P2-AC7 | ✅ | `TRANSACTION_VOID` → 200 `void_logged`; đơn liên quan **không đổi trạng thái** (vẫn `PROCESSING` như trước); log adapter có dòng cảnh báo kèm mã đơn + mã giao dịch, không có khoá |
| P2-AC8 | ✅ | `POST /webhook/sepay` khi tắt → 404 `{"detail":"Webhook biến động số dư đang tắt…"}` |
| P2-AC9 | ✅ | `GET /healthz` → 200 |

### P3 — Lõi ghi nhận giao dịch cổng (BE)
| Mã | Kết quả | Bằng chứng |
|---|---|---|
| P3-AC1 | ✅ | Đơn 150.500đ + IPN đủ tiền → `PaymentTransaction(source=GATEWAY, match_status=MATCHED)`, **1** `SalesInvoice`, batch `qty_available` giảm đúng số kg (FEFO), `DeliveryNote.status=PREPARING`, đơn `PROCESSING` |
| P3-AC2 | ✅ | Đơn `AUTO_CANCELLED` (qua job TTL thật `cancel_expired_orders`) + IPN → `match_status=ORPHAN`, đơn **không** khôi phục |
| P3-AC3 | ✅ | Đơn 165.000đ, IPN 100.000đ → `UNDERPAID`, đơn vẫn `BOOKED` |
| P3-AC4 | ✅ | Đơn 310.000đ, IPN 400.000đ → `MATCHED` 310.000đ + dòng `-THUA` riêng 90.000đ, cả hai `source=GATEWAY` |
| P3-AC5 | ✅ | Đơn đã `MATCHED` qua cổng, gửi thêm IPN khác mã giao dịch cùng đơn → `OVERPAID`, không tạo hoá đơn thứ 2 (đếm lại `SalesInvoice` = 1) |
| P3-AC6 | ✅ | Chủ xác nhận tay mã `FT-UC5-A` (qua `POST /confirm-payment`, user `qa_chu`) → IPN về sau **cùng** mã `FT-UC5-A` → không tạo dòng mới (đếm `PaymentTransaction.filter(bank_txn_id="FT-UC5-A")` = 1) |
| P3-AC7 | ✅ | Chủ xác nhận tay `FT-UC5-B` 280.000đ → IPN về sau **khác** mã (`SEPAY-GATEWAY-TXN-999`) cùng 280.000đ → dòng `OVERPAID` có `duplicate_warning="Nghi trùng xác nhận tay, đối chiếu sao kê trước khi hoàn"`, **thấy được qua API** `GET /api/sales/payments/` với `qa_chu` |
| P3-AC8 | ✅ | Test cả 2 chiều: `SEPAY_ENV=SANDBOX` → giao dịch ghi `environment=SANDBOX`; đổi sang `PRODUCTION` (restart, không sửa code) → giao dịch mới ghi `environment=PRODUCTION`; lọc được qua `?environment=` (field có trong serializer) |
| P3-AC9 | ✅ | `migrate` trên DB mới sạch không lỗi; 3 giao dịch demo cũ (`source=WEBHOOK`) vẫn hiển thị đúng qua API sau migration, `environment=""` |

### P4 — Shop, luồng thanh toán (FE)
Chạy bằng **build thật** (`NEXT_PUBLIC_USE_MOCK=0`), Playwright thật, **chặn điều hướng
thật ra `pay-sandbox.sepay.vn` bằng `page.route()`** rồi soi payload form POST — không mock
giao diện, không gọi ra ngoài. Script giữ lại: `frontend/e2e/qa_sepay_checkout.py`.

| Mã | Kết quả | Bằng chứng |
|---|---|---|
| P4-AC1 | ✅ | Mobile 390px + desktop 1280px: thấy mã đơn, tổng tiền, đồng hồ TTL, nút "Thanh toán bằng VietQR", không còn chuỗi `VIETQR\|ORDER` trong HTML. Ảnh: `shots/qa-p4-mobile-390-02-payment-panel.png` |
| P4-AC2 | ✅ | Bấm nút → form POST bị chặn, kiểm **11 field đúng thứ tự** `merchant,operation,payment_method,order_amount,currency,order_invoice_number,order_description,success_url,error_url,cancel_url,signature`; `order_amount` là số nguyên; không có `test-secret` trong `post_data` |
| P4-AC3 | ✅ | Quay về `?result=success` trước khi bắn IPN → hiện "Đang chờ xác nhận thanh toán…", **không** hiện "Đã thanh toán". Ảnh: `qa-p4-mobile-390-03-waiting.png` |
| P4-AC4 | ✅ | Bắn IPN thật qua adapter (không F5 tay) → sau ≤ 1 chu kỳ poll (5s) trang tự chuyển "✓ Đã thanh toán, đang soạn hàng", `Trạng thái giao hàng: PREPARING`. Ảnh: `qa-p4-mobile-390-04-paid.png` |
| P4-AC5 | ✅ | Quay về `?result=cancel` → "Bạn đã huỷ thanh toán. Đơn vẫn được giữ chỗ." + nút "Thanh toán lại"; `?result=error` → "Thanh toán chưa thành công, bạn có thể thử lại." Ảnh: `qa-p4-retry-01-cancel-return.png` |
| P4-AC6 | ✅ | Đơn hết TTL thật (qua job `cancel_expired_orders`) → "Đơn đã hết hạn giữ hàng, vui lòng đặt lại." + nút "Đặt đơn mới"; **không** có nút "Thanh toán lại". Ảnh: `qa-p4-expired-01.png` |
| P4-AC7 | ✅ | Quay về từ `success_url` (session vừa đặt hàng cùng tab) → không cần gõ lại mã đơn/SĐT (tự điền từ `sessionStorage`) |
| P4-AC8 | ✅ | `NEXT_PUBLIC_USE_MOCK=1 npm run build` sạch (0 lỗi); chunk giả lập (`351.*.js`) tồn tại trong `out/` nhưng **không** được HTML hay JS chunk nào của bản build thật tham chiếu (`grep` xác nhận) |

Kiểm thêm ngoài AC: bấm "Thanh toán lại" lần 2 cho 1 đơn → hậu tố `-2` đúng (Q5), cùng
`order_amount`; quét toàn bộ `out/` (HTML + JS) không có `purchase_rate`, `landed_unit_cost`,
`test-secret`/`SEPAY_SECRET_KEY`.

### P5 — Tổng đơn nguyên đồng (BE)
| Mã | Kết quả | Bằng chứng |
|---|---|---|
| P5-AC1 | ✅ | Unit test có sẵn xanh + **kiểm sống**: đặt đơn 0,125kg × 150.500đ qua Shop API thật → `total_amount="18813.00"` (half-up), dòng đơn vẫn `18812.50`; `checkout/` trả `order_amount=18813` |
| P5-AC2 | ✅ | Unit test có sẵn (`test_p5_ac2_percent_discount_total_is_whole_dong`) xanh, đọc code xác nhận đúng công thức |
| P5-AC3 | ✅ | Tạo thẳng 1 đơn `BOOKED` với `total_amount="18812.50"` (mô phỏng đơn cũ trước khi vá) → `checkout/` trả `order_amount=18813` (làm tròn tại chỗ); `order.total_amount` trong DB **không bị sửa ngược** (vẫn `18812.50`, đúng bất biến #3/#8) |

## Ngoại lệ & biên
- 0 / âm / vượt tồn: không phát sinh field mới (P1-P5 không đụng số lượng bán) — không có
  ca riêng.
- Lô cuối / TTL vừa hết: kiểm bằng job TTL thật (`cancel_expired_orders`, không giả lập)
  → BOOKED có `booked_expires_at` quá khứ bị huỷ đúng, checkout đơn đó bị từ chối (P1-AC4).
- Trùng/đồng thời:
  - Webhook/IPN gửi 2 lần: P2-AC3 (đã ✅ ở trên).
  - "Bấm đúp" nút thanh toán (double-click ở FE) và đua giữa 2 request `checkout/` cùng
    lúc: **chưa kiểm bằng test đa luồng thật trong lần này**. Lý do: khoá chống trùng dùng
    `select_for_update()` trong `checkout.py`, nhưng DB QA dùng SQLite — Django backend
    SQLite **không** áp dụng khoá dòng thật cho `SELECT ... FOR UPDATE` (no-op), nên test đa
    luồng trên SQLite không phản ánh đúng hành vi Postgres (production/Cloud SQL). Đọc code:
    thiết kế (`transaction.atomic()` + `select_for_update()` + tăng `checkout_attempts`)
    đúng chuẩn để chống đua trên Postgres. **Đề xuất**: xác nhận lại bằng test đa luồng thật
    trên Postgres ở bước P6 (đã ghi vào mục Lỗi bên dưới, mức Low, không chặn duyệt vì rủi
    ro thấp — tệ nhất là 2 request cùng nhận trùng hậu tố lần thử, không mất tiền/lộ giá vốn/
    sai tồn kho).
  - "2 đơn tranh 1 lô": thuộc cơ chế FEFO/giữ chỗ đã có từ trước (`sellable_batches`,
    BR-BH-05/06/11), **không đổi bởi P1-P5** — ngoài phạm vi lần QA này, không hồi quy vì
    không đụng file liên quan (đã xác nhận qua diff phạm vi sửa của từng dev-notes).
- Chứng từ không bị xoá: `SalesInvoice`, `PaymentTransaction` là append-only trong mọi kịch
  bản đã thử (UNDERPAID/OVERPAID/ORPHAN/VOID đều chỉ *thêm* dòng, không xoá/sửa dòng cũ);
  `TRANSACTION_VOID` không đổi đơn/kho (BR-TT-16, đã kiểm P2-AC7).
- AuditLog Tầng 2: `confirm-payment` (S11) do `qa_chu` gọi — hành vi ghi audit là code cũ
  không đổi bởi hồ sơ này, không kiểm lại chi tiết audit log lần này (ngoài phạm vi thay
  đổi của P1-P5); đã xác nhận **permission** đúng (xem bảng dưới).

## Phân quyền (bảng Group × hành động)
| Hành động | chu | quan_ly | nv_kho | nv_giao | chưa đăng nhập |
|---|---|---|---|---|---|
| `GET /api/sales/payments/` (hàng chờ lệch, có `duplicate_warning`, `environment`) | 200 | 403 | 403 | 403 | 401 |
| `POST /api/sales/orders/{id}/confirm-payment` (S11) | 200 | 403 | 403 | 403 | 401 |
| `POST /api/shop/orders/{code}/checkout/` (Shop công khai, P1) | 200 (không cần đăng nhập, đúng thiết kế guest checkout) | | | | 200 |
| `GET /api/inventory/batches/` (kiểm không lộ giá vốn, không phải AC của hồ sơ này nhưng kiểm hồi quy) | — | — | 200, **không có** `purchase_rate`/`landed_unit_cost` | — | — |

Không phát sinh quyền mới (đúng như phân tích §4 "Không phát sinh quyền mới"). Hàng chờ và
xác nhận tay vẫn chỉ Chủ — khớp BR-PQ và ranh giới "việc làm tiền rời túi" là của Chủ.

## Rò giá vốn
- Shop JSON (`/api/shop/catalog/`, `/api/shop/orders/`, `/api/shop/orders/{code}/`,
  `/api/shop/orders/{code}/checkout/`): `grep -i "purchase_rate|landed_unit_cost|cost"` →
  **sạch** ở cả 4 endpoint.
- Toàn bộ static export Shop (`out/*.html`, `out/_next/static/chunks/*.js`) bản build thật:
  **sạch** `purchase_rate`, `landed_unit_cost`, `gia_von`, `profit`, `lai_lo`; **sạch**
  chuỗi khoá `test-secret`/`SEPAY_SECRET_KEY`.
- `GET /api/sales/payments/` (Chủ) có field mới `environment`, `duplicate_warning` —
  **không** phải field giá vốn, không vi phạm bất biến #1.
- `nv_kho` xem `GET /api/inventory/batches/` (hồi quy, không phải field mới của hồ sơ này):
  không có `purchase_rate`/`landed_unit_cost`.

## Hồi quy
| Mục | Lệnh | Kết quả |
|---|---|---|
| Backend (toàn bộ) | `manage.py test` | **582 passed, 0 failed** |
| Backend migrations | `manage.py makemigrations --check --dry-run` | sạch |
| Adapter (toàn bộ) | `pytest -q` | **67 passed** |
| Frontend Shop build (mock) | `NEXT_PUBLIC_USE_MOCK=1 npm run build` | sạch, 0 lỗi |
| Frontend Shop build (thật) | `NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=... npm run build` | sạch, 0 lỗi; xác nhận API_BASE đúng trong bundle |
| ERP console | `tsc --noEmit` | sạch |
| ERP console | `npm run build` | sạch, 18 route tĩnh |
| ERP e2e mock S7 (khung console) | `e2e/s7_shell.py` | tất cả PASS (đếm dòng, không có tổng số in sẵn) |
| ERP e2e mock S8 (views/dashboard) | `e2e/s8_views.py` | **47/47 PASS** |
| ERP e2e mock S10+S11 (đơn & tiền) | `e2e/s10_s11_orders.py` | **90/90 PASS** |
| ERP e2e mock S12+S13 (hàng chờ, hoàn) | `e2e/s12_s13_queue.py` | **100/100 PASS** |
| ERP e2e mock S14+S16 (huỷ/hoàn) | `e2e/s14_s16_cancel_refund.py` | **43/43 PASS** |
| Shop e2e | Không tìm thấy script `shop_e2e` sẵn có trong repo (`frontend/e2e/` trống trước khi QA thêm) — dùng script QA mới `frontend/e2e/qa_sepay_checkout.py` thay thế cho phạm vi P4 | PASS (xem bảng P4 ở trên) |

Không hồi quy nào đỏ. Không sửa `backend/apps/**` ngoài thư mục `tests/` (thực ra QA lần
này **không thêm test mới vào `backend/apps/*/tests/`** — dev đã phủ đủ AC bằng unit test
tự viết rất chi tiết, khớp đúng từng AC; QA chỉ kiểm chứng độc lập bằng gọi API/adapter
sống + đọc lại test có sẵn để xác nhận không phải test rỗng).

## Lỗi
### B1 — Chưa kiểm chống đua thật (double-click / 2 request `checkout/` cùng lúc) trên Postgres · Low · P1-AC5 (ngoại lệ)
**Bước tái hiện:** đọc `apps/sales/payments/checkout.py` — khoá chống trùng hậu tố dùng
`transaction.atomic()` + `SalesOrder.objects.select_for_update()`. Trên SQLite (DB QA dùng
tại máy), `SELECT ... FOR UPDATE` không khoá dòng thật (giới hạn của backend SQLite trong
Django), nên một test đa luồng ở môi trường này sẽ không phản ánh đúng hành vi production
(Cloud SQL Postgres, nơi khoá này có tác dụng thật).
**Mong đợi:** 2 request `checkout/` gần như đồng thời cho cùng đơn → 2 hậu tố khác nhau
(`-2`, `-3`), không trùng.
**Thực tế:** chưa đo được bằng thực nghiệm trong phiên này (thiếu Postgres tại máy QA).
**Ảnh hưởng:** thấp — kể cả nếu có đua thật trên SQLite dev, hậu quả tệ nhất là 2 lần gọi
cùng nhận **cùng** một `order_invoice_number` (không mất tiền, không sai tồn kho, không lộ
giá vốn) vì adapter vẫn bóc mã gốc đúng và Django vẫn chống trùng theo `bank_txn_id` ở tầng
IPN. **Không chặn duyệt.** Đề xuất: thêm 1 test `TransactionTestCase` + `threading` chạy
trên Postgres thật ở bước P6 (deploy sandbox) để xác nhận trước khi mở Shop công khai.

## Lệnh đã chạy (kèm output tóm tắt)
```bash
cd backend && .venv/bin/python manage.py test
# Ran 582 tests in 24.734s — OK

cd backend && .venv/bin/python manage.py makemigrations --check --dry-run
# No changes detected

cd adapter && .venv/bin/python -m pytest -q
# 67 passed, 1 warning in 0.25s

cd frontend && NEXT_PUBLIC_USE_MOCK=1 npm run build   # sạch
cd frontend && NEXT_PUBLIC_API_BASE=http://localhost:8123 NEXT_PUBLIC_USE_MOCK=0 npm run build  # sạch

cd erp-console && ./node_modules/.bin/tsc --noEmit && npm run build   # sạch
cd erp-console && python3 e2e/s7_shell.py     # tất cả PASS
cd erp-console && python3 e2e/s8_views.py     # 47/47 PASS
cd erp-console && python3 e2e/s10_s11_orders.py   # 90/90 PASS
cd erp-console && python3 e2e/s12_s13_queue.py    # 100/100 PASS
cd erp-console && python3 e2e/s14_s16_cancel_refund.py  # 43/43 PASS

cd frontend && python3 e2e/qa_sepay_checkout.py   # mobile 390 + desktop 1280, tất cả PASS

# Kiểm chữ ký độc lập (P1-AC1), khớp byte-for-byte với BE:
python3 -c "
import hmac, hashlib, base64
s = 'merchant=QA_MERCHANT,operation=PURCHASE,payment_method=BANK_TRANSFER,order_amount=18813,currency=VND,order_invoice_number=SO260926-F828D1,order_description=Thanh toan don SO260926-F828D1,success_url=...,error_url=...,cancel_url=...'
print(base64.b64encode(hmac.new(b'test-secret', s.encode(), hashlib.sha256).digest()).decode())
"
# Tfl2aIDf9MtZoWbuXeM4dCA5kyLOrVSQGt6JUQQxiKE=  — khớp BE

# Ví dụ IPN giả lập gửi tới adapter (không gọi SePay thật):
curl -X POST http://127.0.0.1:8199/ipn/sepay -H "X-Secret-Key: test-secret" -d '{...}'
```

## Ghi chú môi trường (không phải lỗi sản phẩm)
- Lần đầu build Shop trỏ Django tạm bị chặn CORS (Django mặc định `CORS_ALLOWED_ORIGINS`
  rỗng — hành vi đúng, an toàn theo mặc định). QA tự thêm biến môi trường
  `CORS_ALLOWED_ORIGINS=http://localhost:3410` khi chạy tại máy, **không sửa code**. Khi
  deploy thật (P6/production), Ops cần đặt `CORS_ALLOWED_ORIGINS` trỏ đúng domain Firebase
  `cangca-loc` — đã có sẵn cơ chế qua env, chỉ cần cấu hình đúng giá trị.
