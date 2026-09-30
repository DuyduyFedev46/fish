# Ghi chú hiện thực — P8 Sửa lỗi review P1–P7

## Lô 1 — BE
> be-dev (Claude) · 2026-09-30 · Story: SR-01, SR-03 · Chưa commit (chờ QA + điều phối).

### Số test gốc / sau
- Gốc (trước Lô 1, `manage.py test` không --parallel): **1065 test, OK**.
- Sau (lượt đầu): 1072 test, OK (+7 = `test_p8_cost_keys_scan.py`). Sau khi điều phối thêm 2 `__init__.py` và sửa L1–L3: **1140 test, OK**.
- **Phát hiện (đã xử lý bởi điều phối, thêm 2 `__init__.py`):** `backend/apps/ai/execution/` **không có `__init__.py`** (namespace package) nên
  `manage.py test` mặc định **không chạy bất kỳ test nào trong `apps/ai/execution/tests/`** (44 test cũ + 13 test SR-03 mới).
  Chạy tường minh: `manage.py test apps.ai.execution.tests` → **57 test, OK** (44 cũ + 13 mới). Cùng lỗi ở
  `backend/apps/content/entries/tests/` (thiếu `__init__.py` trong thư mục tests). Đề xuất điều phối cho phép thêm 2 file `__init__.py` rỗng
  (chạy lại full suite để chắc 57 test này + test content xanh khi vào full run).

### Sửa theo review Tech Lead (03b, L1–L3)
- L1 `test_p8_close_batch_sold.py`: ma trận Group assert đúng **404** + `code == "COMMAND_UNKNOWN"` (chốt: đúng thiết kế); thêm ca đối chứng
  dương `chu` gọi cùng lệnh/lô → 200 `scheduled` trong cùng test. Mục "Lệch thiết kế" 1 bên dưới đã được chốt (404 đúng, ô 403 trong story là lỗi viết).
- L2 `run_due_ai_actions.py::_mark_failed`: `select_related("owner").select_for_update(skip_locked=True, of=("self",))` — chỉ khoá dòng
  `AiAction`, không khoá dòng `auth_user`.
- L3 `test_p8_cost_keys_scan.py`: sentinel giá vốn chỉ tìm trong `changes` + `note` của từng dòng (không gồm `created_at` micro giây).
- Điều phối đã thêm `backend/apps/ai/execution/__init__.py` và `backend/apps/content/entries/tests/__init__.py` (xem "Phát hiện" bên dưới; đã xử lý).

### File đã sửa / thêm
- Sửa `backend/apps/common/cost_keys.py` — thêm 8 khoá vào `COST_KEYS`: `loss_amount`, `loss`, `inventory_value`, `margin`, `gross_profit`,
  `expired_cost`, `supplier_refund_amount`, `supplier_return_cost` (02b §1.1).
- Sửa `backend/apps/ai/execution/safety.py` — `payment_transaction__order_id__in` → `payment_transaction__sales_order_id__in`;
  `PaymentTransaction.filter(order_id__in=…)` → `sales_order_id__in=…`. Đọc lại toàn file: không còn lookup `order` sai khác.
- Sửa `backend/apps/ai/management/commands/run_due_ai_actions.py` — tách thân mỗi việc thành `_process_one(act, registry)`; vòng lặp
  `try/except Exception` **ngoài** `transaction.atomic()` của từng việc; `_mark_failed(action_pk, exc)` mở transaction MỚI, đọc lại
  `select_for_update(skip_locked=True)` và chỉ đổi khi còn `SCHEDULED` → `FAILED`, `downgrade_reason={"code": "AI_JOB_ERROR", "text": …}`,
  ghi AuditLog `fail_<command>` (`actor=None, actor_kind="ai", ai_actor=owner, ai_level="B"`, không `changes`, `note` cố định); log
  `AI job failed action=<id> cmd=<mã lệnh> err=<tên lớp exception>` (không `str(exc)`, không args). Bước đẩy việc quá hạn 2 giờ tách thành
  `_escalate_overdue` và cũng bọc try riêng từng việc. Nếu chính `_mark_failed` lỗi: log tên lớp, job vẫn chạy tiếp.
- Thêm `backend/apps/accounts/audit/tests/test_p8_cost_keys_scan.py` (7 test).
- Thêm `backend/apps/ai/execution/tests/test_p8_close_batch_sold.py` (13 test; chuyển từ R1 của `repro/`; dùng lại fixture
  `CloseBatchAiTests._create_fully_eligible_batch` của DW-25 **không kế thừa** để không chạy lại test cũ).
- Không đụng: `migrations/`, `models/`, `cancel_expired_batch`, dữ liệu `AuditLog`, frontend/erp-console. Không có migration
  (`makemigrations --check --dry-run` → "No changes detected").
- Không có endpoint mới, contract API không đổi.

### BR / bất biến
- SR-01: bất biến 1, BR-PQ-13, BR-GV-03, BR-LO-03 (Chủ vẫn thấy `loss_amount`; Quản lý không; lọc khi trả ra ở `redact_cost`,
  không sửa bảng AuditLog — bất biến 4).
- SR-03: BR-LO-04, BR-KK-05, DW-25-AC4, DW-21, DW-23; bất biến 9 (log không chứa nội dung exception).
- `redact_cost` cũng được `ai/policy/rules.py::SCRUB_COST_KEYS` (= `COST_KEYS`) và `ai/registry/api.py` dùng → 8 khoá mới cũng bị lọc
  khỏi kết quả lệnh AI/registry với người thiếu `view_costprice` (đúng ý bảo vệ giá vốn; toàn bộ test cũ vẫn xanh).

### TDD — output ĐỎ (trước khi sửa code)
SR-01 (`manage.py test apps.accounts.audit.tests.test_p8_cost_keys_scan`) — 4 failures / 7:
```
FAIL: test_sr01_ac1_quan_ly_khong_thay_loss_amount
AssertionError: 'loss_amount' unexpectedly found in {'status': {'from': 'EXPIRED', 'to': 'CANCELLED'}, 'loss_amount': '812340.0000000', 'qty': '10.000'}
FAIL: test_sr01_ac3_cost_keys_co_du_khoa_tien
AssertionError: Lists differ: ['loss_amount', 'loss', 'inventory_value', ... 'supplier_return_cost'] != []
FAIL: test_sr01_ac3_quet_khoa_tien_quan_ly_khong_thay_gia_von
AssertionError: '101234' unexpectedly found in '{"count": 4, ... "loss_amount": "1012340.0000000" ...
FAIL: test_sr01_ac3_redact_cost_bo_khoa_tien_o_moi_do_sau
AssertionError: {'detail': [{'expired_cost': 1, 'gross_profit': 1, ...
Ran 7 tests ... FAILED (failures=4)
```
SR-03 (`manage.py test apps.ai.execution.tests.test_p8_close_batch_sold`) — 12 errors + 1 failure / 13:
```
ERROR: test_sr03_ac1_lo_da_ban_khong_van_field_error            django.core.exceptions.FieldError: Unsupported lookup 'order_id' for ForeignKey or join on the field not permitted.
ERROR: test_sr03_ac2a_phieu_hoan_pending_theo_hoa_don_chan_chot     (cùng FieldError)
ERROR: test_sr03_ac2a_phieu_hoan_pending_theo_giao_dich_chan_chot   (cùng FieldError)
ERROR: test_sr03_ac2b_giao_dich_open_cua_don_chan_chot              (cùng FieldError)
ERROR: test_sr03_ac2_giao_dich_da_xu_ly_khong_chan                  (cùng FieldError)
ERROR: test_sr03_ac3_job_khong_chet_voi_lo_da_ban_viec_sau_van_chay (FieldError thoát khỏi call_command)
ERROR: test_sr03_ac3_lo_da_ban_con_phieu_hoan_pending_thi_escalated (FieldError thoát khỏi call_command)
ERROR: test_sr03_ac4_exception_bat_ky_thanh_failed_viec_sau_van_chay_idempotent   RuntimeError: loi gia SECRET-KHACH-GIA-0900000123 (thoát khỏi job)
ERROR: test_sr03_ac4_thay_doi_dang_do_cua_viec_loi_bi_rollback      ValueError: gia (thoát khỏi job)
ERROR: test_sr03_ac4_mark_failed_khong_de_len_viec_da_doi_trang_thai  AttributeError: module ... has no attribute '_mark_failed'
ERROR: test_sr03_ac5_api_chu_lo_da_ban_khong_500                    FieldError (API 500)
ERROR: test_sr03_ac5_api_chu_lo_da_ban_con_giao_dich_open_ha_muc_c  FieldError
FAIL:  test_sr03_ma_tran_group_lenh_chot_lo   AssertionError: 404 != 403 (ql_dw25, COMMAND_UNKNOWN) — xem "Lệch thiết kế" bên dưới
Ran 13 tests ... FAILED (failures=1, errors=12)
```
(Ca `test_sr03_ma_tran_group_lenh_chot_lo` đỏ vì kỳ vọng ban đầu 403 sai với thiết kế sẵn có, không phải lỗi code; đã sửa assert, xem dưới.)

### TDD — output XANH (sau khi sửa)
```
manage.py test apps.accounts.audit.tests.test_p8_cost_keys_scan       -> Ran 7 tests  OK
manage.py test apps.ai.execution.tests.test_p8_close_batch_sold        -> Ran 13 tests OK
manage.py test apps.ai.execution.tests   (44 cũ + 13 mới)              -> Ran 57 tests OK
DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test    -> Ran 1140 tests OK  (sau L1–L3 + 2 __init__.py; gốc 1065)
manage.py makemigrations --check --dry-run                             -> No changes detected
```

### Bằng chứng chống "xanh giả"
- SR-01-AC3: test khẳng định trước (a) đủ 3 dòng audit `recompute_landed_cost`/`cancel_expired_batch`/`close_batch` có trong DB, (b) khoá
  `loss_amount` thật sự nằm trong DB (fixture có khoá nhạy cảm), (c) đếm `ok_responses > 0` (mọi trang của `GET /api/audit-logs/` với
  `quan_ly` trả 200), (d) quét đệ quy mọi `changes` không còn khoá ∈ `COST_KEYS`, (e) JSON không chứa `81234`, `101234`, `812340`,
  `1012340`; Chủ vẫn thấy `1012340`.
- Ma trận Group `/api/audit-logs/`: chu 200 (thấy `loss_amount`), quan_ly 200 (không thấy), nv_kho/nv_giao/cskh 403, khách 401.
- SR-03: ca lô đã bán chạy hết đường job → DONE (lô CLOSED), ca còn phiếu hoàn/giao dịch OPEN → ESCALATED cho `chu`; việc xếp sau vẫn DONE;
  việc PENDING quá 2 giờ vẫn được đẩy lên `chu`; mock `dispatch_command` văng `RuntimeError` chứa sentinel PII giả → việc `FAILED`, log
  (bắt bằng `assertLogs`) không chứa sentinel/`str(exc)`, có id + mã lệnh + `RuntimeError`; thay đổi dở dang bị rollback; chạy lần 2 không
  dispatch lại (`call_count == 0`) và không thêm dòng `fail_*`.

### Lệch thiết kế / giả định
1. **Ma trận SR-03 ghi 403 cho `quan_ly`/`nv_kho`/`nv_giao`/`cskh` gọi `inventory.batch.close`**, nhưng registry ẩn lệnh với người thiếu quyền
   nên thực tế trả **404 `COMMAND_UNKNOWN`** (thiết kế cũ, không đổi trong lô này). Test assert `status in (403, 404)` + không tạo `AiAction`;
   khách 401. Nếu Duy muốn đúng 403, đó là đổi hành vi registry → ngoài Lô 1, cần quyết định riêng.
2. Story SR-01-AC1 ghi giá vốn "81.234" và sentinel `812340`; số học đúng cần đơn giá 81234 đ/kg (× 10 kg = 812340) → fixture dùng 81234.
3. `apps/ai/execution/__init__.py` và `apps/content/entries/tests/__init__.py` thiếu (xem "Phát hiện" ở trên) — chưa sửa vì ngoài danh sách
   được sửa của Lô 1.
4. `_mark_failed` dùng `skip_locked=True` (nhất quán với phần còn lại của job): nếu một tiến trình khác đang giữ khoá dòng, việc giữ nguyên
   `SCHEDULED` và lần chạy sau xử lý lại — không mất việc.

### Nợ / lưu ý cho QA
- SR-03-AC5 chỉ kiểm bằng test backend (`POST /api/ai/commands/inventory.batch.close/call/` lô đã bán → 200 `scheduled`; có giao dịch OPEN → 200
  `proposal` hạ mức C).
- Không có việc FE trong phần BE này.

## Lô 1 — SR-02 (điều phối viên, 2026-09-30)
- AC1 (tái hiện, trước khi sửa): `cd erp-console && npm ci`
  ```
  npm error code ERESOLVE
  npm error ERESOLVE could not resolve
  npm error peerOptional @types/node@"^22.0.0 || >=24.0.0" from vitest@5.0.2
  ```
- Sửa: `erp-console/package.json` `@types/node` `^20.14.0` → `^22.0.0`; `npm install` (không cờ) sinh lại lock.
  Diff `package-lock.json`: chỉ khối `@types/node` 20.19.43 → 22.20.4 (+ dòng devDependencies). Không thêm/bớt thư viện khác (AC4).
- AC2: `rm -rf node_modules && npm ci` ở `erp-console` → `added 189 packages`, thoát 0, không ERESOLVE. `frontend`: `npm ci` sạch từ trước, không sửa.
- AC3: `erp-console`: `tsc --noEmit` OK · `next build` OK · vitest 9 files / 79 tests passed. `frontend`: `tsc` OK · build OK.
- Không phải sửa file type nào (điểm dừng "> 5 file" không chạm).
- Ghi chú máy: `~/.npm` có file thuộc root (EACCES) → chạy `npm ci --cache <scratchpad>`; không ảnh hưởng dự án.

## Lô 1 — điều phối: test không được discovery (ngoài danh sách file của Lô 1, ghi lệch)
- be-dev phát hiện `backend/apps/ai/execution/` và `backend/apps/content/entries/tests/` thiếu `__init__.py` → `manage.py test`
  bỏ qua 57 + 11 test (gồm 13 test SR-03). Điều phối thêm 2 file `__init__.py` rỗng (không đổi hành vi sản phẩm).
- Sau khi thêm: `manage.py test` → `Ran 1140 tests … OK` (trước: 1072). `makemigrations --check --dry-run` → No changes detected.
- Repro R1 gốc (`repro/review_repro_tests.py`) chạy lại: `test_r1_safety_crashes_for_sold_batch` → `AssertionError: Exception not raised`
  (lỗi đã hết), `test_r1_job_poison_pill` → `R1 job: no crash`, trạng thái `DONE`.
