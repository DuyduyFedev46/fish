# Ghi chú phát triển — Sửa lỗi bảo mật có sẵn (L-1, L-3, L-5, L-6, robots staging) + L-10, L-11

## Baseline ban đầu (trước Lô 1)
- Lệnh kiểm chứng: `cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run`
- Kết quả: `Ran 667 tests in 68.036s. OK`
- Migrations: `No changes detected`

## Lô 1: S01 (L-3), S02 (L-6), S03 (L-5)
- Trạng thái: QA APPROVED, commit `91a9fc3`, push thành công `wip/autosave`.

### Danh sách file thực hiện:
- `backend/apps/common/cost_keys.py` (mới): `COST_KEYS` frozenset, `can_view_cost(user)`, `redact_cost(value)`.
- `backend/apps/common/throttling.py` (mới): `SettingsRateThrottle`, `ShopLookupIpThrottle`, `ShopLookupOrderThrottle`, `ShopOrderCreateThrottle`, `ShopCheckoutThrottle`, `LoginIpThrottle`, `LoginUserThrottle`.
- `backend/apps/common/api.py`: `exception_handler` xử lý `Throttled` -> HTTP 429 `{"detail": "...", "code": "throttled"}` kèm header `Retry-After`.
- `backend/apps/common/audit.py`: docstring nhắc quy ước không đưa số giá vốn vào `note`.
- `backend/apps/accounts/audit/serializers.py`: `audit_item` lọc `changes` qua `redact_cost` khi `can_view_cost=False`.
- `backend/apps/accounts/audit/api.py`: `AuditLogListView.get` tính `can_view_cost(request.user)` một lần và truyền vào serializer.
- `backend/apps/sales/orders/shop_api.py`: `ShopOrderLookupView` kiểm regex `\d{4}` (400 `LOOKUP_BAD_LAST4`), so khớp 4 số cuối SĐT đã lọc số (404 `LOOKUP_NOT_FOUND`), gắn throttle; `ShopOrderCreateView` gắn `ShopOrderCreateThrottle`.
- `backend/apps/sales/payments/shop_api.py`: `ShopOrderCheckoutView` dùng chung thông điệp 404 `LOOKUP_NOT_FOUND`, gắn `ShopCheckoutThrottle`.
- `backend/apps/accounts/auth/api.py`: `LoginTokenView` gắn `LoginIpThrottle` và `LoginUserThrottle`.
- `backend/config/settings.py`: Thêm `NUM_PROXIES` và cấu hình `CAVEVE_THROTTLE_RATES` đọc từ env (tắt mặc định khi `TESTING`).
- Tests mới:
  - `backend/apps/common/tests/test_cost_keys.py`: 6 tests
  - `backend/apps/accounts/audit/tests/test_l3_cost_redaction.py`: 5 tests
  - `backend/apps/sales/orders/tests/test_l6_lookup.py`: 6 tests
  - `backend/apps/common/tests/test_l5_throttle.py`: 8 tests

### Lệch thiết kế:
- Không có. Tuân thủ 100% tài liệu thiết kế `02b-tech-design.md`.

### Kết quả kiểm chứng thực tế:
1. `cd backend && .venv/bin/python manage.py test apps.accounts.audit apps.common apps.sales`:
   `Ran 337 tests in 23.903s. OK`
2. `grep -rn "throttle" backend/config/settings.py backend/apps/common/throttling.py`:
   - `backend/config/settings.py:200:# --- Giới hạn tần suất throttle (S03 / L-5, doc/features/2026-09-28-sua-loi-bao-mat) ----`
   - `backend/apps/common/throttling.py:2:Lớp throttle cho các endpoint công khai (S03 / L-5, doc/features/2026-09-28-sua-loi-bao-mat).`
3. `cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run`:
   `Ran 692 tests in 63.235s. OK` (tăng 25 tests từ 667 lên 692, không có migration phát sinh).

## Lô 2: S04 (L-1), S05 (robots staging)
- Trạng thái: BE & Hosting hoàn thành, kiểm chứng xanh, chuyển QA

### Danh sách file thực hiện:
- `backend/apps/inventory/batches/services.py`:
  - Thêm `OPEN_ORDER_STATUSES = ("BOOKED", "PAID", "PROCESSING")`.
  - `@transaction.atomic` và `Batch.objects.select_for_update().get(pk=batch.pk)` trước mọi phép kiểm.
  - Thứ tự kiểm tra: (1) is_closed -> BR-LO-05; (2) tồn > 0 -> BR-LO-04; (3) qty_reserved > 0 -> BR-LO-04; (4) còn đơn mở -> BR-LO-04 (đếm distinct số đơn, thông điệp không rò PII); (5) ReturnToStock DRAFT -> BR-LO-04; (6) Purchase Invoice -> BR-LO-04; (7) Kiểm kê APPROVED bắt buộc và không có DRAFT -> BR-KK-05.
- `backend/apps/inventory/batches/tests/test_services.py`:
  - Sửa duy nhất `test_publish_and_close_batch` thêm phiếu kiểm kê APPROVED cho lô trước khi chốt theo quy định mới BR-KK-05.
- `backend/apps/inventory/batches/tests/test_l1_close_batch.py` (mới):
  - 17 test cases bao phủ chi tiết AC1 đến AC6.
- `frontend/firebase.staging.json`: Thêm header `X-Robots-Tag: noindex, nofollow` cho `"source": "**"`.
- `erp-console/firebase.staging.json`: Thêm header `X-Robots-Tag: noindex, nofollow` cho `"source": "**"`.
- `doc/ops/moi-truong.md`: Bổ sung 1 dòng ghi chú kiểm tra noindex staging sau khi deploy.
- Sửa nhỏ phục vụ build `erp-console` (tồn đọng từ commit WIP 75d5200):
  - `erp-console/features/audit/components/AuditLogScreen.tsx`: sửa đường dẫn `./audit.module.css` thành `../audit.module.css`.
  - `erp-console/features/ai/runtime/wllama.ts`: thêm `/// <reference path="./wllama.d.ts" />`.
  - `erp-console/features/ai/runtime/worker-manager.ts`: ép kiểu `(this.pending as Pending | null)?.id`.

### Sửa test cũ có chủ đích:
- `backend/apps/inventory/batches/tests/test_services.py:test_publish_and_close_batch`: Thêm phiếu kiểm kê APPROVED vì theo BR-KK-05 lô không thể chốt nếu chưa kiểm kê.

### Lệch thiết kế:
- Không có.

### Kết quả kiểm chứng thực tế:
1. `cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run`:
   `Ran 712 tests in 60.502s. OK` (tăng thêm 20 tests so với Lô 1, tổng cộng tăng 45 tests so với baseline). `No changes detected`.
2. `cd frontend && node -e 'JSON.parse(require("fs").readFileSync("firebase.staging.json","utf8"))' && npx tsc --noEmit && NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=https://cangca-api-staging-675411800433.asia-southeast1.run.app npm run build`:
   Thành công (8/8 static pages).
3. `cd erp-console && node -e 'JSON.parse(require("fs").readFileSync("firebase.staging.json","utf8"))' && npx tsc --noEmit && npm run build`:
   Thành công (21/21 static pages).
4. `git diff --exit-code frontend/firebase.json erp-console/firebase.json`:
   Exit code 0 (file production hoàn toàn không bị thay đổi).
- Nhắc việc: Kiểm tra `curl -sI https://cangca-loc-staging.web.app/shop/ | grep -i x-robots-tag` và `https://cangca-erp-staging.web.app/` sẽ được Duy thực hiện sau khi deploy staging.
