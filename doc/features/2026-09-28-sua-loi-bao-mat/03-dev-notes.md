# Ghi chú phát triển — Sửa lỗi bảo mật có sẵn (L-1, L-3, L-5, L-6, robots staging) + L-10, L-11

## Baseline ban đầu (trước Lô 1)
- Lệnh kiểm chứng: `cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run`
- Kết quả: `Ran 667 tests in 68.036s. OK`
- Migrations: `No changes detected`

## Lô 1: S01 (L-3), S02 (L-6), S03 (L-5)
- Trạng thái: BE hoàn thành, kiểm chứng xanh, chuyển QA

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
