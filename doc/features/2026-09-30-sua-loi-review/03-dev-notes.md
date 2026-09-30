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

## Lô 2 — FE

**SR-07 — Nháp "Nhập lô" không giữ giá mua giữa các người dùng (BM-04, bất biến 1 phía FE).** Xong, chưa commit.

### File
- Thêm `erp-console/features/purchasing/components/draftStorage.ts`: `saveDraft(userId, draft)` (bỏ `lines[].rate` và mọi trường lạ qua `sanitize`; giữ `idempotencyKey` của chính người đó), `loadDraft(userId)` (cũng bỏ `rate` nếu dữ liệu cũ còn), `resolveIdempotencyKey(userId, generate)`, `clearDraft(userId)`, `purgeLegacyDraft()`, `clearAllDrafts()` (xoá mọi khoá `cave_draft_nhap_lo*` ở `sessionStorage` và `localStorage`). Khoá `cave_draft_nhap_lo:<userId>`, lưu `sessionStorage`.
- Thêm `erp-console/features/purchasing/components/draftStorage.test.ts` (8 test vitest, SR-07-AC1/AC2/AC4 + nháp hỏng + không có `window`).
- Sửa `erp-console/features/purchasing/components/NhapLoForm.tsx`: bỏ đọc/ghi `localStorage`; lấy `userId` từ `useAuth().me.id`; nạp nháp qua `loadDraft` (ô giá mua luôn rỗng); idempotency key: xem mục "Sửa L1" bên dưới; mở form gọi `purgeLegacyDraft()` dọn khoá cũ có giá mua; gửi thành công gọi `clearDraft`.
- Sửa `erp-console/features/auth/components/AuthProvider.tsx` (hàm `logout`): thêm `clearNhapLoDrafts()` (= `clearAllDrafts` của `draftStorage`) cạnh `clearAllDrafts()` chung của `shared/lib/drafts`.
- Thêm `erp-console/e2e/sr07_nhap_lo_draft.py` (Playwright Python, mock).

### TDD
Đỏ trước: `vitest run features/purchasing/components/draftStorage.test.ts` → `Error: Cannot find module './draftStorage'` (Test Files 1 failed, no tests). Sau khi viết `draftStorage.ts` → 8/8 xanh. Cả bộ `npm test`: 10 file, 87 test xanh. `tsc --noEmit` sạch, `npm run build` sạch.

### Bằng chứng AC3 (Playwright, mock, dữ liệu giả, 12/12 PASS)
Ảnh: `qa-lo2/sr07-1-chu-go-gia-81234.png` (Chủ gõ giá 81234), `qa-lo2/sr07-2-nv-kho-o-gia-rong.png` (nv_kho `kho1` sau khi Chủ đăng xuất: ô giá rỗng), `qa-lo2/sr07-3-f5-cung-nguoi.png` (F5 cùng người: giữ số lượng, giá rỗng).
Các bước kiểm: khoá cũ `cave_draft_nhap_lo` (đặt sẵn, có giá) bị dọn khi mở Nhập lô; Chủ đang gõ 81234 mà local/sessionStorage không chứa 81234, nháp nằm ở `sessionStorage` khoá `cave_draft_nhap_lo:1`; sau đăng xuất không còn khoá `cave_draft_nhap_lo*` nào; `kho1` mở Nhập lô: ô giá mua và ô số lượng rỗng, storage không chứa 81234; F5 cùng người: số lượng còn, giá rỗng, storage không chứa giá.
Cách chạy: `cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build`, copy `out/` sang thư mục riêng, `(cd <thư mục>/out && python3 -m http.server 3212 &)`, `python3 e2e/sr07_nhap_lo_draft.py` (đặt `BASE` nếu đổi cổng), rồi tắt server. Script tự đặt khoá cũ giả để kiểm việc dọn. QA giữ nguyên ảnh + bước này khi ghi `04-qa-report.md`.

### Lệch / nợ (cần điều phối biết)
1. `erp-console/features/purchasing/api.ts` còn `DRAFT_STORAGE_KEY`, `getNhapLoDraft`, `saveNhapLoDraft`, `clearNhapLoDraft` (localStorage, khoá cũ, có thể chứa `rate`) và được `purchasing.test.ts` (DW-17-AC3) dùng. Không còn nơi nào trong UI gọi chúng, nhưng chúng ngoài danh sách file được sửa nên giữ nguyên. Đề nghị Lô 7 (SR-23/24) xoá 3 hàm này cùng test DW-17-AC3 cũ hoặc chuyển test sang `draftStorage`.
2. `AuthProvider` (module `auth`) import `draftStorage` của module `purchasing` — ngược quy ước "module không import vào ruột module khác", nhưng đúng chỉ dẫn story ("logout gọi `clearAllDrafts()`"). Nếu muốn sạch hơn: đưa hàm dọn nháp Nhập lô vào `shared/lib/drafts.ts`.
3. Hành vi đổi có chủ ý: idempotency key không còn được giữ qua F5/mở lại form (SR-07-AC4), nên nếu gửi phiếu bị lỗi mạng rồi tải lại trang mà bấm gửi lại thì dùng key mới (BE dựa vào key để chống trùng nên có khả năng tạo phiếu thứ hai nếu lần trước thực ra đã thành công). Đã theo đúng story; QA lưu ý nếu cần bàn thêm với Duy.
4. Không đổi cách xử lý 401 hết phiên (giữ nháp theo S7-AC6): nháp Nhập lô còn lại chỉ có mặt hàng/số lượng/hạn dùng, ở `sessionStorage`.

## Lô 2 — BE
> be-dev (Claude) · 2026-09-30 · Story: SR-04, SR-05 (cùng commit), SR-06 · Chưa commit (chờ QA + điều phối).

### Số test
- Gốc (đầu Lô 2, `manage.py test` không --parallel): **1155 OK**. Sau: **1186 OK** (+31: `test_p8_pii_sweep` 10, `test_p8_scrub_pii` 6, `test_p8_scope` 15).
- `makemigrations --check --dry-run` → No changes detected (không migration, không model, không endpoint mới, contract không đổi).

### File đã sửa / thêm
- Sửa `backend/apps/ai/policy/rules.py` — `SCRUB_PII_KEYS` thêm `customer`, `recipient_phone`, `recipient_phone_masked`, `phone_last4`, `phone_masked`, `customer_address`.
  `scrub.py` **không phải sửa**: `scrub_data` đã `continue` (bỏ cả nhánh dict/list/chuỗi) với khoá thuộc tập PII; test AC2 chứng minh.
- Sửa `backend/apps/ai/registry/discovery.py` — hằng `STANDARD_DETAIL_ACTIONS = {retrieve, partial_update, update, destroy}` → `detail=True` (kèm `target="detail"`);
  action khác giữ `getattr(action_func, "detail", False)`; APIView theo mẫu `<pk>|<id>|<str:|<int:` (tách hàm `_path_has_lookup`).
- Sửa `backend/apps/ai/execution/pipeline.py` (chỉ bước 6 + `import re`) — view không có `get_object` (APIView) không còn `AttributeError`; xem "Lệch thiết kế" 1.
- Thêm `backend/apps/sales/orders/scope.py::scope_orders_for(user, qs)` (chuyển nguyên logic từ `SalesOrderViewSet.get_queryset`: full scope → tất cả; cskh → phiếu trong phạm vi gọi hoặc đã gọi; còn lại → phiếu gán cho mình, `distinct()`).
- Sửa `backend/apps/sales/orders/api.py` (chỉ `get_queryset` + bỏ import `has_full_delivery_scope` không còn dùng) — gọi `scope_orders_for`.
- Sửa `backend/apps/sales/orders/next_steps.py` (chỉ khối lọc của `get_order_guidance`) — thay khối `nv_giao` riêng bằng `scope_orders_for`; `Http404("Không tìm thấy đơn hàng")` cố định (không lặp mã do người gọi gửi).
- Sửa `backend/apps/ai/actions/services.py` (chỉ `escalate_guidance_step`, import cục bộ) — `Http404`/`PermissionDenied` (Django + DRF) từ provider được re-raise → 404/403; lỗi khác → `BusinessError("Không thể nạp chứng từ.", DOC_NOT_FOUND, 400)`, **không** in nguyên văn exception; log chỉ `type(exc).__name__`. Escalate lọc phạm vi qua provider `order` (đã dùng `scope_orders_for`) nên không có khối lọc riêng để thay.
- Thêm test: `backend/apps/ai/registry/tests/test_p8_pii_sweep.py`, `backend/apps/ai/execution/tests/test_p8_scrub_pii.py`, `backend/apps/sales/orders/tests/test_p8_scope.py`. Không sửa/xoá test cũ.

### BR / bất biến
Bất biến 9 (SR-04: 6 khoá PII, bỏ cả nhánh, kể cả với Chủ), BR-PQ-12 + BR-GH-18 + Tầng 3 (SR-06, một hàm phạm vi), H7 (SR-05: `sales.salesorder.partial_update` vẫn bị cấm hẳn), BR-AI-09 (AiAction.args không chứa PII).

### TDD — ĐỎ (trước khi sửa code)
SR-05 (`manage.py test apps.ai.registry.tests.test_p8_pii_sweep`, code chưa sửa) — 6 failures + 1 error / 8 (lúc đó chưa có test AC3):
```
FAIL test_sr05_ac1_chu_retrieve_lo_tra_du_lieu      AssertionError: 502 != 200 : {"code":"AI_DISPATCH_FAILED"}   (DRF: Expected view BatchViewSet to be called with a URL keyword argument named "pk")
FAIL test_sr05_ac2_moi_lenh_retrieve_va_partial_update_co_detail   catalog.bundleline.partial_update phải có detail=True
FAIL test_sr05_ac3_nv_giao_de_xuat_partial_update_ngoai_pham_vi_404_khong_tao_ai_action   200 != 404 : {"outcome":"proposal",...} (chỉ discovery.py hoàn nguyên: tạo đề xuất cho phiếu ngoài phạm vi)
ERROR test_sr05_ac4_batch_pnl_kem_target_id_khong_500  AttributeError: 'BatchPnlView' object has no attribute 'get_object'
FAIL test_sr04_ac3_retrieve_don_hang_chu_thanh_cong_khong_pii / test_sr04_ac3_quet_moi_lenh_doc_...   502 not less than 500 : catalog.bundleline.retrieve chu -> 502
FAIL test_sr04_ac1_nv_kho_dashboard_khong_lo_ten_khach / ..._chu_...   'Khách Giả Bí Mật' unexpectedly found in {"recent_orders":[{"customer":"Khách Giả B"...
```
Sau khi CHỈ sửa SR-05 (discovery + pipeline) — xác nhận thứ tự commit 02b §2.2: `retrieve` mở ra thì **lộ PII**:
```
FAIL test_sr04_ac3_retrieve_don_hang_chu_thanh_cong_khong_pii   'Khách Giả Bí Mật' unexpectedly found in {"id":1,"code":"SO...","customer":{"name":"Khách Giả Bí Mật"...
FAIL test_sr04_ac3_quet_moi_lenh_doc_...   Lệnh AI rò PII: [('reports.dashboard_summary', chu|quan_ly|nv_kho, 'Khách Giả Bí Mật' / key:customer / key:phone_last4),
     ('sales.salesinvoice.list|retrieve', chu|quan_ly|nv_kho, 'key:customer'), ('sales.salesorder.retrieve', chu|quan_ly|nv_kho|cskh, 'Khách Giả Bí Mật' / key:customer)]
```
SR-04-AC2 (`manage.py test apps.ai.execution.tests.test_p8_scrub_pii`, trước khi sửa `rules.py`) — 6 failures / 6: `{'code': 'SO-1', 'customer': 'Khách Giả Bí Mật'} != {'code': 'SO-1'}`; `'customer' not found in frozenset({...})`.
SR-06 (`manage.py test apps.sales.orders.tests.test_p8_scope`, có `scope.py` nhưng chưa nối guidance/escalate) — 8 failures / 15:
```
test_sr06_ac1_cskh_don_ngoai_pham_vi_404              200 != 404 : {"doc":{"type":"order","code":"DH-OUT-1",...
test_sr06_ac1_body_404_khong_lo_thong_tin             200 != 404
test_sr06_ac3_cskh_het_pham_vi_khi_task_xong_va_chua_goi   200 != 404
test_sr06_ac3_user_gan_quyen_truc_tiep_theo_pham_vi_viewset  200 != 404
test_sr06_ac2_cskh_escalate_don_ngoai_pham_vi_404     400 != 404 : {"code":"STEP_NOT_FOUND"}
test_sr06_ac2_nv_giao_escalate_don_khac_404           400 != 404 : "Không thể nạp chứng từ order #DH-OUT-1: Không tìm thấy đơn hàng: DH-OUT-1" (DOC_NOT_FOUND, in nguyên văn exception)
test_sr06_ac2_thieu_quyen_xem_don_403                 400 != 403 : DOC_NOT_FOUND
test_sr06_ac3_guidance_khong_lo_pii_khach             lỗi fixture của tôi (mã giao dịch giả chứa SĐT giả) -> đã sửa fixture, không phải rò
```

### TDD — XANH
```
manage.py test apps.ai.registry.tests.test_p8_pii_sweep      -> Ran 10 tests OK
manage.py test apps.ai.execution.tests.test_p8_scrub_pii     -> Ran 6 tests OK
manage.py test apps.sales.orders.tests.test_p8_scope         -> Ran 15 tests OK
DJANGO_DEBUG=1 env -u DATABASE_URL manage.py test            -> Ran 1186 tests OK   (gốc 1155)
manage.py makemigrations --check --dry-run                   -> No changes detected
```

### Bằng chứng chống "xanh giả"
- Test quét (SR-04-AC3) duyệt **52 lệnh đọc** x 5 Group (chu, quan_ly, nv_kho, nv_giao, cskh), lệnh `detail` thử mọi khoá tra cứu của fixture (pk + mã đơn/lô/hàng/hoá đơn) → **101 response 200, trong đó 39 là `retrieve` thành công** (test assert `ok_total > 0` và `retrieve_ok > 0`; mọi response phải < 500). Sentinel: "Khách Giả Bí Mật", `0900000123`, "Số 1 Đường Giả", "NGUYEN VAN GIA" (`raw_payload` của giao dịch) — chuỗi và cả khoá (`customer`, `phone_last4`, tập `SCRUB_PII_KEYS`) đều không được xuất hiện.
- Dashboard: assert mã đơn vẫn hiện (có dữ liệu thật, không rỗng).
- SR-05-AC3 có ca đối chứng dương (gán phiếu cho nv_giao → đề xuất tạo được) và ca xác nhận `sales.salesorder.partial_update` vẫn 404 với mọi Group (H7).
- SR-06 ma trận: chu/quan_ly/nv_kho 200 mọi đơn; nv_giao 200 đơn phiếu mình, 404 đơn khác; cskh 200 trong phạm vi / 404 ngoài / 404 khi phiếu rời hàng chờ; user gán quyền trực tiếp: 404 → 200 sau khi gán phiếu (guidance và chi tiết đơn cho cùng kết quả); khách 401; thiếu quyền 403; `scope_orders_for` khớp `GET /api/sales/orders/` cho 7 user; guidance không chứa tên/SĐT/địa chỉ.

### Điểm dừng
**Không chạm.** Test quét chỉ thấy PII ở: `reports.dashboard_summary` (customer, phone_last4) và `sales.salesorder.retrieve` (nhánh `customer`); `sales.salesinvoice.list/retrieve` chỉ có KHOÁ `customer` (là id khách, không có sentinel). Đều nằm trong nhánh `customer`/dashboard → không cần allowlist.

### Lệch thiết kế / giả định / nợ
1. **SR-05-AC4 và `dispatch.py`**: `dispatch_command` (ngoài danh sách file Lô 2) chỉ truyền 1 tham số URL tên `lookup_field` (mặc định `pk`). Hai APIView đọc có `detail=True` — `reports.batch_pnl` (`<str:batch_id>`) và `common.guidance` (`<doc_type>/<doc_id>`) — sẽ `TypeError` → 502. Trong bước 6 tôi chặn sớm: nếu view không có `get_object` và tập tham số URL ≠ {lookup_field} → **400 `BR-AI-01` "Lệnh này chưa hỗ trợ gọi theo mã đối tượng qua AI."** (AC4 cho phép 200 hoặc 400 có thông điệp). Hai lệnh này trước đây cũng không chạy được (500 AttributeError) nên không hồi quy. Muốn chạy được thật cần sửa `dispatch.py` (ánh xạ tên tham số từ `spec.path`) — đề nghị điều phối quyết định, có thể để P9.
2. **SR-05-AC3 dùng `delivery.deliverynote.partial_update`** thay vì `sales.salesorder.partial_update` như story: lệnh của đơn bị registry cấm hẳn (H7, không lật) nên không tồn tại; cơ chế phạm vi cần kiểm là như nhau (Tầng 3 qua `get_object`). Story nên sửa chữ này.
3. Escalate: story/02b nói "thay khối lọc riêng trong `ai/actions/services.py:299-302`" nhưng lọc phạm vi thực chất nằm ở provider `order` (đã đổi ở `next_steps.py`); phần sửa trong `services.py` là chỗ nuốt exception (A1). Hệ quả cho các provider khác (`batch`, `refund`, `payment`): 404/403 cũng đi thẳng ra thay vì 400 — nhất quán nhưng là đổi hành vi (test cũ vẫn xanh).
4. `sales.salesinvoice.*` hết khoá `customer` trong kết quả AI (id khách) do bỏ cả nhánh — chấp nhận theo 02b §2.1.
5. Test `test_sr06_ac1_body_404_khong_lo_thong_tin` kỳ vọng `detail` chứa "Không tìm thấy đơn hàng" (body chung của 02b §2.3).

### Sửa L1 (techlead review Lô 2, cùng lô)
Idempotency key nằm trong nháp `sessionStorage` khoá `cave_draft_nhap_lo:<userId>` (vẫn không lưu `rate`). Khi mở form: `resolveIdempotencyKey(userId, generateUUID)` — có key trong nháp của CHÍNH người này thì dùng lại (F5 rồi gửi lại sau lỗi mạng vẫn cùng key, BE chống trùng được), không có thì sinh mới. Gửi thành công: xoá nháp + sinh key mới (`NhapLoForm.tsx`). Nháp người khác không đọc được (khoá theo userId); đăng xuất `clearAllDrafts()` xoá hết nên không bao giờ dùng lại key. Thay đổi: `draftStorage.ts` (thêm `idempotencyKey?` + `resolveIdempotencyKey`), `NhapLoForm.tsx`, `draftStorage.test.ts` (thay test "không lưu key" bằng (a) F5 cùng user giữ key, (b) user khác/sau đăng xuất key mới, (c) sau gửi thành công key mới, + nháp có key vẫn không chứa `rate`; 11 test), `e2e/sr07_nhap_lo_draft.py` (thêm assert key + luồng gửi thành công → nhập phiếu tiếp; 18/18 PASS, thêm ảnh `qa-lo2/sr07-4-sau-gui-thanh-cong-key-moi.png`). `tsc --noEmit`, `npm run build` sạch; `npm test` 10 file, 90 test xanh. Ghi chú: nếu gửi lỗi mạng rồi F5 và key được giữ đúng thiết kế; mục nợ 3 cũ (nguy cơ phiếu trùng) không còn.

## Lô 3 — FE

**Story:** SR-09-AC4 (BR-GH-18, CS-08/CS-09) — màn gọi CSKH nhận 409 `STALE_STATE` từ `POST /api/cskh/queue/<id>/calls/`.

### Đã sửa (`erp-console/features/cskh/`)
- `api.ts`: thêm `isStaleStateError(err)` (ApiError status 409 + `code === "STALE_STATE"`). Không đổi contract/hàm gọi API.
- `CskhCallModal.tsx`: state `staleMessage`. Khi `recordCskhCall` ném 409 STALE_STATE thì hiện hộp `role="alert"` (`data-testid="cskh-stale-alert"`) với đúng `detail` của BE + nút **Tải lại**; nút này gọi `onUpdated()` (nạp lại hàng chờ) rồi `onClose()` (đóng modal). Khi đang stale, mọi nút kết quả cuộc gọi bị khoá (`actionsBlocked`) nên không gửi lại trên màn cũ. Hộp tự cuộn vào khung nhìn (mobile: nút kết quả nằm dưới, hộp nằm đầu thân modal). Lỗi khác vẫn hiện ở hộp lỗi chung như cũ. Chỉ xử lý cuộc gọi; đổi người nhận / huỷ xác nhận / quyết định Quản lý chưa gắn xử lý STALE_STATE (BE story chỉ đổi `record_call`).
- `cskh.module.css`: `.staleBox` (flex, xuống dòng, nút cao 44px). Dùng lại `alertError`/`btnPrimary` sẵn có, không thêm màu mới.
- `mock.ts`: (1) phiếu mock mới `note_id 36` / `DH-260928-0036` (dữ liệu giả) trong `MOCK_STALE_ON_CALL_IDS`: lần ghi cuộc gọi đầu tiên, mock mô phỏng job `auto_cancel_overdue` đã chạy trước (phiếu CANCELLED, task REFUND_CALL) rồi trả 409. (2) `mockRecordCskhCall` theo BE: phiếu CANCELLED mà không phải REFUND_CALL, hoặc REFUND_CALL với kết quả ∉ {UNREACHABLE, NOTIFIED} → 409 `{"detail": "Đơn đã bị huỷ — tải lại màn hình.", "code": "STALE_STATE"}` (trước đây nhánh CANCELLED trả 400 BR-GH-07). (3) Sửa lỗi có sẵn của mock: `mockGetCskhQueue` đọc `req.url` (không tồn tại, MockRequest chỉ có `path`) nên lọc `?state=` (tab Báo hoàn tiền, Hẹn gọi lại…) không bao giờ chạy trong mock; nay đọc `req.url ?? req.path`.
- `cskh.test.ts`: +9 test vitest (SR-09 AC1/AC3b, AC2 tham số hoá 5 kết quả bị chặn, NOTIFIED/UNREACHABLE vẫn 201, luồng thuận 201, `isStaleStateError`); `beforeEach` khôi phục phiếu 36.
- `erp-console/e2e/sr09_ac4_stale_state.py` (mới): Playwright, 2 ca (1280x800 và 375x667), 11 assert mỗi ca.

### Bằng chứng
- Playwright `sr09_ac4_stale_state.py` (bản build mock, cổng 3213): **22/22 PASS**. Luồng: đăng nhập `cs1` → `/cskh/` → mở phiếu DH-260928-0036 → bấm "Đã xác nhận" → thấy đúng câu "Đơn đã bị huỷ — tải lại màn hình." + nút Tải lại (cao ≥ 44px, nằm trong khung nhìn, không cuộn ngang, nút kết quả bị khoá) → bấm Tải lại → modal đóng, phiếu rời hàng chờ mặc định và xuất hiện ở tab "Báo hoàn tiền"; console không chứa SĐT/tên.
- Ảnh (dữ liệu giả): `qa-lo3/sr09-ac4-{desktop-1280,mobile-375x667}-{1-thong-diep-409,2-sau-tai-lai,3-tab-bao-hoan-tien}.png`.
- `tsc --noEmit` sạch; `npm run build` sạch; `npm test` 10 file, 99 test xanh (gốc 90).

### Lệch / nợ
- Không lệch contract: dùng đúng body `{detail, code}` như story. Cần BE Lô 3 (`record_call`) trả 409 đúng mã để chạy thật; FE chưa thử với BE thật.
- Chỉ xử lý STALE_STATE ở ghi cuộc gọi; các thao tác khác trong modal (đổi người nhận, huỷ xác nhận, quyết định Quản lý) khi đơn đã huỷ vẫn hiện lỗi chung bằng `detail`, chưa có nút Tải lại.

## Lô 3 — BE
> be-dev (Claude) · 2026-09-30 · Story: SR-08, SR-09 (BE), SR-10, SR-11 · Chưa commit (chờ QA + điều phối).

### Số test gốc / sau
- Gốc (trước Lô 3, `manage.py test` không --parallel): **1202 test, OK**.
- Sau: **1241 test, OK** (+39 = 11 SR-08, 8 SR-10, 11 SR-09, 9 SR-11). `makemigrations --check --dry-run` → "No changes detected".
- Không có migration, không có endpoint mới, contract API không đổi (chỉ thêm mã lỗi 409 mới ở endpoint có sẵn, xem SR-09).

### File đã sửa / thêm
- Sửa `backend/apps/inventory/batches/services.py`: `publish_batch` (`@transaction.atomic` + `select_for_update().get(pk)` rồi mới kiểm DRAFT, thao tác trên object đã khoá); `check_cancel_expired_batch` (thêm BR-LO-07); thêm hằng `RESERVING_ORDER_STATUSES = ("BOOKED",)`, hàm `_open_orders_count(batch, statuses)` và `_fmt_kg(qty)` (định dạng `2,000`).
- Sửa `backend/apps/inventory/batches/next_steps.py`: bước `cancel_expired` gọi `check_cancel_expired_batch` → `missing` có BR-LO-07, `allowed = can_cancel and not missing_biz`; đổi dòng import (thêm `check_cancel_expired_batch`).
- Sửa `backend/apps/delivery/cskh/services.py` (chỉ `record_call`): thay kiểm `BR-GH-07 "Đơn đã huỷ."` bằng `ConflictError("Đơn đã bị huỷ — tải lại màn hình.", code="STALE_STATE")` (HTTP 409).
- Sửa `backend/apps/sales/payments/auto_confirm.py`: bộ lọc quét thêm `match_status=UNMATCHED`; `_escalate_to_chu` idempotent (xem dưới).
- Thêm test: `backend/apps/inventory/batches/tests/test_p8_cancel_expired_reserved.py` (R5), `test_p8_publish_lock.py` (R3), `backend/apps/delivery/tests/test_p8_record_call_stale.py` (R2), `backend/apps/sales/payments/tests/test_p8_auto_confirm_idempotent.py` (R4).
- Không đụng: `check_close_batch`/`close_batch`, `cancel_receipt`, `auto_cancel_overdue`, `migrations/`, `models/`, FE, `doc/decisions.md`, `02*.md`.

### Endpoint / contract thực tế
- `POST /api/inventory/batches/<id>/cancel-expired/` (chỉ `chu`): lô EXPIRED còn giữ chỗ → 400
  `{"detail": "Còn 2,000 kg đang giữ chỗ của 1 đơn — chờ đơn thanh toán hoặc hết hạn giữ chỗ rồi huỷ.", "code": "BR-LO-07"}`.
  Body chỉ có `detail`, `code` (không tên/SĐT khách, không giá vốn).
- `GET /api/guidance/batch/<id>/`: bước `cancel_expired` khi còn giữ chỗ: `allowed=false`, `missing=[{"code": "BR-LO-07", "text": "Còn 2,000 kg đang giữ chỗ của 1 đơn — …"}]` (+ BR-PQ-12 nếu thiếu quyền).
- `POST /api/inventory/batches/<id>/publish/` (chu, quan_ly): lô đã huỷ/không DRAFT → 400 `{"detail": "Chỉ publish được lô đang ở trạng thái Nháp.", "code": "BR-MH-05"}`.
- `POST /api/cskh/queue/<note_id>/calls/` trên đơn đã huỷ → **409** `{"detail": "Đơn đã bị huỷ — tải lại màn hình.", "code": "STALE_STATE"}` (kiểm bằng API thật: `resp.json() == {"detail": ..., "code": "STALE_STATE"}`, `exception_handler` render `ConflictError.extra` rỗng). Ghi UNREACHABLE/NOTIFIED trên REFUND_CALL vẫn 201 như cũ.
- Job DW-26 `process_exact_payment_matches`: không có endpoint.

### Rule BR đã cài
- BR-LO-07 (mới, SR-08): không huỷ lô quá hạn khi còn giữ chỗ (chỉ đếm đơn BOOKED, đúng nơi `qty_reserved` phát sinh; đơn PAID/PROCESSING đã trừ kho nên không chặn). Không tự nhả giữ chỗ/huỷ đơn khách; giữ chỗ hết theo TTL. (Văn bản BR vào spec là việc Lô 5.)
- BR-LO-03 (huỷ 2 lần vẫn 400, không ghi ledger), BR-MH-05 (publish có khoá), BR-GH-18/CS-08/CS-09 (SR-09), DW-26/V-DW1 (SR-11), BR-PQ-04/05 (audit không nhân bản). Bất biến 9: response 409/400 và audit không chứa SĐT/tên/địa chỉ (test sentinel giả).

### TDD — output ĐỎ (trước khi sửa code)
Repro R2–R5 chạy trên code cũ (`review_repro.tests`, 4 test "OK" vì chỉ `print`, in ra hành vi sai):
```
R2 after auto-cancel: CANCELLED CANCELLED REFUND_CALL
R2 after CONFIRMED: CANCELLED PREPARING DONE          <- phiếu đã huỷ bị kéo về PREPARING
R3 receipt: CANCELLED batch: SELLING qty: 0.000       <- mở bán lô của phiếu đã huỷ
R4 audit rows after 2 runs: 2 | action after reject + run: ESCALATED   <- nhắc lặp + mở lại việc Chủ đã từ chối
R5 before cancel: avail 100.000 reserved 2.000
R5 after cancel: status CANCELLED avail 0.000 reserved 2.000
R5 confirm_payment raised: BusinessError Xuất vượt tồn lô CA-THU-…: còn 0.000kg, cần 2.000kg.
R5 order: BOOKED | txn: None                          <- mất giao dịch tiền
```
Test chính thức trên code cũ:
```
test_p8_cancel_expired_reserved + test_p8_publish_lock  -> Ran 19, FAILED (failures=11)
  FAIL test_sr08_ac1_r5_khong_huy_lo_khi_con_giu_cho            AssertionError: 200 != 400
  FAIL test_sr08_ac1_service_raise_business_error_...           AssertionError: BusinessError not raised
  FAIL test_sr08_ac2_thanh_toan_van_thanh_cong_sau_khi_bi_chan_huy  200 != 400
  FAIL test_sr08_ac4_guidance_cancel_expired_khong_allowed_...  True is not false
  FAIL test_sr10_ac1_r3_publish_object_cu_sau_khi_huy_phieu_bi_chan  BusinessError not raised
  FAIL test_sr10_ac2_doc_lai_co_khoa_dong_roi_moi_kiem_draft    Expected 'select_for_update' to be called once. Called 0 times.
  FAIL test_sr10_ac2_object_cu_khong_bi_ghi_de_...              BusinessError not raised
  (+ ma trận Group, đếm 2 đơn, không-rò: cùng lỗi 200 != 400)
test_p8_record_call_stale                                -> Ran 11, FAILED (failures=6, errors=3)
  FAIL test_sr09_ac1_r2_confirmed_sau_tu_huy_409_stale_state    AssertionError: ConflictError not raised
  ERROR test_sr09_phieu_cancelled_task_khong_phai_refund_call_cung_409  BusinessError: Đơn đã huỷ.  (mã cũ BR-GH-07, 400)
  FAIL test_sr09_ac4_api_409_body_detail_code / ma_tran (không 409)
test_p8_auto_confirm_idempotent                          -> Ran 9, FAILED (failures=8)
  FAIL test_sr11_ac1_r4_chay_2_lan_chi_1_dong_audit             AssertionError: 2 != 1
  FAIL test_sr11_ac2_viec_da_dong_khong_bi_mo_lai_...           AssertionError: 18 != 6
  FAIL test_sr11_ac2_r4_rejected_roi_chay_lai                   'ESCALATED' != REJECTED
  FAIL test_sr11_ac4_chi_quet_unmatched                         AssertionError: 3 != 0
```
### TDD — output XANH (sau khi sửa)
```
manage.py test apps.inventory.batches.tests.test_p8_cancel_expired_reserved apps.inventory.batches.tests.test_p8_publish_lock  -> 19 OK
manage.py test apps.delivery.tests.test_p8_record_call_stale                                                                   -> 11 OK
manage.py test apps.sales.payments.tests.test_p8_auto_confirm_idempotent                                                       -> 9 OK
manage.py test apps.inventory.batches (98) · apps.delivery (133) · apps.sales.payments (133)                                    -> OK
DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test    -> Ran 1241 tests OK   (gốc 1202)
manage.py makemigrations --check --dry-run                             -> No changes detected
```
Repro R2–R5 chạy lại **2 lần** sau khi sửa (job chạy lặp), hai lần cho kết quả giống hệt: R2, R3, R5 nay ném đúng lỗi nghiệp vụ ở bước sai (script tái hiện không bắt exception nên hiện "ERROR" — nghĩa là lỗi đã bị chặn), R4 ổn định:
```
R2: ConflictError: Đơn đã bị huỷ — tải lại màn hình.                (services.py record_call)
R3: BusinessError: Chỉ publish được lô đang ở trạng thái Nháp.       (services.py publish_batch)
R5: BusinessError: Còn 2,000 kg đang giữ chỗ của 1 đơn — chờ đơn thanh toán hoặc hết hạn giữ chỗ rồi huỷ.
R4 audit rows after 2 runs: 1 | action after reject + run: REJECTED
```
(cả hai lần đều giống nhau; R5 trước lỗi in `avail 100.000 reserved 2.000`, lô không bị huỷ nên `confirm_payment` không còn chạm vào lô đã xoá tồn.)

### Bằng chứng chống "xanh giả" / ma trận
- SR-08: ma trận `POST …/cancel-expired/`: chu → 400 nghiệp vụ (đối chứng có 400 thật), quan_ly/nv_kho/nv_giao/cskh → 403, khách → 401, dữ liệu không đổi; AC2 thanh toán sau khi bị chặn → có `PaymentTransaction` MATCHED + `SalesInvoice`; AC3 job TTL (`cancel_unpaid_expired`) → giữ chỗ 0 → huỷ 200 với đúng 1 `WRITE_OFF = -qty_available`; đơn đã trả tiền không chặn; đếm đúng "5,000 kg … 2 đơn".
- SR-10: ma trận `POST …/publish/`: chu 200, quan_ly 200 (không có `purchase_rate`/`landed_unit_cost` trong JSON — quét bằng `COST_KEYS`), nv_kho/nv_giao/cskh 403, khách 401, publish lại 400 `BR-MH-05`; đối chứng: lô vẫn DRAFT sau các lần 403. Chứng minh khoá: `Batch.objects.select_for_update` được gọi đúng 1 lần (spy, vì test chạy SQLite nên FOR UPDATE thật không quan sát được); object cũ không ghi đè `status/qty` lên lô đã huỷ.
- SR-09: ma trận: cs1/chu/quan_ly (có `confirm_with_customer`) CONFIRMED → 409 `STALE_STATE`, NOTIFIED/UNREACHABLE → 2xx; nv_kho/nv_giao → 403; khách → 401. Tham số hoá `CONFIRMED, CONFIRMED_CHANGED, CALLBACK, WRONG_NUMBER, WANT_CANCEL, WANT_CHANGE` (mỗi ca kiểm phiếu vẫn CANCELLED, task vẫn REFUND_CALL, không thêm `CustomerCall`/audit). Response 409 không chứa SĐT/tên/địa chỉ giả.
- SR-11: 6 trạng thái kết thúc `REJECTED/DONE/CANCELLED/EXPIRED/UNDONE/FAILED` × 2 lần chạy: giữ nguyên, audit không tăng; AC3 lý do đổi → +1 audit + cập nhật `downgrade_reason`, chạy tiếp thì ổn định; audit/`downgrade_reason`/`args` không chứa SĐT/tên giả.

### Lệch thiết kế / giả định
1. **SR-11-AC3: so sánh `downgrade_reason["text"]`, không phải `["code"]`** như 02b §3.4 ("chỉ ghi audit khi … `downgrade_reason["code"]` đổi"). Lý do: mọi lần chuyển Chủ đều dùng `code="AI_MISMATCH"` (chỉ `text` khác nhau), nên so `code` không bao giờ phát hiện lý do đổi và AC3 (số tiền giao dịch cập nhật → +1 audit) không thể đạt. `text` chính là "lý do".
2. **SR-11-AC4 áp dụng cho cả nhánh tự khớp**: bộ lọc quét chuyển sang `match_status=UNMATCHED` cho toàn bộ job (theo 02b). Toàn bộ test DW-26 cũ dùng UNMATCHED nên vẫn xanh; nhánh `p.sales_order is not None → CONFIRM_ORDER` giờ hầu như không tới được (giao dịch UNMATCHED chưa gắn đơn) — không đổi vì nằm ngoài phạm vi.
3. Số `escalated` trong dict kết quả job vẫn đếm cả ca no-op (việc đã đóng / cùng lý do); chỉ Nhật ký và trạng thái việc được bảo vệ. Không đụng tới vì không nằm trong AC.
4. **SR-09: giá trị kết quả không nằm trong danh sách hợp lệ** (`"KHONG_CO"`) trên REFUND_CALL vẫn rơi xuống `400 INVALID_INPUT` (không phải 409) — chỉ 6 kết quả hợp lệ của `CustomerCall.Result` mới là "stale". Story nói "mọi kết quả khác" — hiểu là mọi kết quả hợp lệ khác.
5. **SR-09 phiếu CANCELLED mà task không phải REFUND_CALL**: thông điệp/mã cũ `BR-GH-07 "Đơn đã huỷ." (400)` đổi thành 409 `STALE_STATE` theo 02b §3.2. Không có test cũ nào kiểm nhánh này (grep) nên không phải sửa assert.
6. Story SR-09-AC4 ghi NOTIFIED/UNREACHABLE "200"; API thực tế (và test CS-09 cũ) trả **201** — giữ nguyên 201.
7. SR-08-AC2: story ghi "đơn PAID"; sau `confirm_payment` đơn chuyển thẳng `PROCESSING` (có hoá đơn + phiếu giao). Test kiểm `status ∈ {PAID, PROCESSING}` + có giao dịch MATCHED + hoá đơn.
8. `check_close_batch` (Lô 5, không được đụng) vẫn giữ nguyên câu truy vấn đơn mở inline; hàm `_open_orders_count(batch, statuses)` mới đã tách sẵn để Lô 5 gọi lại thay vì nhân đôi truy vấn.
9. Chưa chạy thử với FE thật ở SR-09-AC4 (fe-dev làm song song); contract BE khớp mô tả FE (`{detail, code: "STALE_STATE"}`, 409).

### Nợ / lưu ý cho QA
- RA-05: việc AI `ESCALATED` vẫn chưa có đường để Chủ đóng (ngoài phạm vi); SR-11-AC2 kiểm bằng cách đặt trực tiếp trạng thái kết thúc trong test.
- RA-03 (`advance_status` không khoá) không sửa (ngoài lô).
- Tranh chấp thật `cancel_receipt` ∥ `publish_batch` (hai transaction song song, PostgreSQL) chưa chạy được ở đây (test dùng SQLite); logic khoá dựa vào cả hai phía cùng `select_for_update` trên dòng lô.

## Lô 4 — BE

Story: SR-12 (chứng từ đảo), SR-13 (báo cáo lô/kỳ/dashboard trừ chứng từ), SR-14 (lệnh lập bù). Chưa commit, chưa deploy, không chạm DB nào ngoài DB test.

### Số test gốc / sau
Toàn bộ `cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test` (không `--parallel`): **1293 → 1341 test, OK, 0 failure** (1327 khi giao lô, +1 test M1, +5 test D1-B, +8 test E1/E2).
Mới: 48 (SR-12 17, SR-13 14, SR-14 17 gồm E1/E2). `makemigrations --check --dry-run`: "No changes detected".

### File đã sửa / thêm
- Mới: `backend/apps/sales/models/credit_notes.py`, `backend/apps/sales/migrations/0011_salescreditnote.py`, `backend/apps/sales/credit_notes/{__init__,services,README}` + `tests/{__init__,base,test_p8_credit_note,test_p8_backfill}.py`, `backend/apps/sales/management/commands/backfill_credit_notes.py`, `backend/apps/reports/tests/test_p8_pnl_credit_note.py`.
- Sửa: `sales/models/__init__.py` (re-export), `sales/orders/services.py` (`cancel_paid_order` gọi service + docstring), `sales/orders/timeline.py` (sự kiện `credit_note_issued`), `sales/refunds/services.py` (chỉ docstring `confirm_refund`), `sales/admin.py` (Admin chỉ đọc), `reports/services.py` (`batch_pnl`, `period_pnl`, docstring), `reports/dashboard_api.py` (chỉ `revenue_today`), `sales/README.md`, `reports/README.md`, `doc/business-process-spec.md` (BR-HT-06, BR-HT-10 mới, BR-BC-03, BR-BC-04, bảng "Lãi lỗ theo lô", chép đúng 02b §4.6, ghi "Duy duyệt 30/09").
- Sửa test cũ (2 chỗ, xem "Lệch"): `reports/tests/test_api.py`, `reports/tests/test_services.py`, `sales/orders/tests/test_privacy_consent.py`.

### Migration
`sales/migrations/0011_salescreditnote.py` (1 file, sinh bằng `makemigrations sales -n salescreditnote`, đã đọc lại): chỉ `CreateModel SalesCreditNote`, `CreateModel SalesCreditNoteLine`, `AddIndex sales_sales_issued__d6f3a9_idx` (`issued_at`). Phụ thuộc `inventory.0003_alter_batch_options`, `sales.0010_grant_view_privacy_consent`. Không đổi bảng cũ, không AlterField nào. `default_permissions=("view",)` cho cả hai model. Chạy trên DB test sạch (bộ test tự `migrate` từ đầu) đạt.

### Endpoint / contract thực tế
Không thêm endpoint. Đổi hành vi + khoá JSON (chỉ THÊM khoá):
- `POST /api/sales/orders/<id>/cancel/` (và job tự huỷ CSKH): response giữ nguyên khoá; sau khi huỷ có 1 `SalesCreditNote` (`DC-<mã hoá đơn>`, `amount = invoice.amount`, dòng theo `SalesInvoiceLineBatch`), hoá đơn vẫn `ISSUED`.
- `GET /api/reports/batch/<batch_id>/` (chỉ chủ): thêm `reversed_qty`, `reversed_revenue`; `revenue`/`qty_sold` đã trừ phần đảo. Mẫu sau huỷ 2 kg × 150.000: `"revenue": 0, "qty_sold": 0, "reversed_qty": 2, "reversed_revenue": 300000`.
- `GET /api/reports/period/?year&month` (chỉ chủ): thêm `credit_notes`, `cogs_reversed`; `revenue = Σ hoá đơn trong kỳ − credit_notes`, `cogs = Σ giá vốn − cogs_reversed`.
- `GET /api/dashboard/summary/`: `kpis.revenue_today` = hoá đơn hôm nay − chứng từ đảo lập hôm nay (không thêm khoá).
- Timeline đơn (`order detail.timeline` và khối guidance): thêm sự kiện `kind="credit_note_issued"`, `label="Lập chứng từ đảo doanh thu DC-… (300.000 ₫)"`, `actor_display` = người huỷ hoặc "Hệ thống"; không có giá vốn/PII.

### Rule BR đã cài
BR-HT-06 (sửa), BR-HT-10 (mới: append-only, cùng transaction với huỷ, idempotent theo `source_key`, tối đa một chứng từ huỷ/hoá đơn, hoá đơn ISSUED nguyên vẹn; nếu hoá đơn không ISSUED → `BusinessError(code="BR-HT-10")`), BR-BC-03, BR-BC-04.

### TDD — ĐỎ (trước khi cài code)
- SR-12 (`red1.txt`): `Ran 16 tests ... FAILED (failures=6, errors=7)` — `AssertionError: 0 != 1` (không có chứng từ nào) 5 lần, `RuntimeError not raised` (service chưa được gọi trong `cancel_paid_order`), còn lại là chưa có sự kiện timeline / chưa đăng ký Admin. (Lần chạy đầu ImportError không tính là đỏ đúng nghĩa nên đã thêm stub rồi mới chạy lại.)
- SR-13 (`red2.txt`): `Ran 9 tests ... FAILED (failures=2, errors=6)` — `KeyError: 'reversed_qty'`; `AssertionError: Decimal('4.000') != Decimal('2')` (bán lại kg đã hoàn cộng hai lần); `450000.0 != 150000.0` (dashboard chưa trừ).
- SR-14 (`red3.txt`): `Ran 9 tests ... FAILED (errors=9)` — `CommandError: Unknown command: 'backfill_credit_notes'`.
- R6 (repro `review_repro_tests.py`): xác nhận trước khi sửa doanh thu lô 300.000 / `qty_sold 2` cho đơn đã huỷ; nay thành test chính thức `SR13PnlCreditNoteTests.test_sr13_ac1_r6_batch_pnl_sau_tu_huy_doanh_thu_ve_0`.

### TDD — XANH
```
manage.py test apps.sales.credit_notes            -> Ran 26 tests ... OK (17 SR-12 + 9 SR-14)
manage.py test apps.reports.tests.test_p8_pnl_credit_note -> Ran 9 tests ... OK
manage.py test (toàn bộ)                          -> Ran 1328 tests in 55.465s ... OK (sau M1)
makemigrations --check --dry-run                  -> No changes detected
```

### Bằng chứng chống "xanh giả" / ma trận
- Đối chứng số: trước huỷ `revenue=300000, reversed_qty=0`; sau huỷ `revenue=0, qty_sold=0`; bán lại 2 kg → `qty_sold=2`, `revenue=300000` (không 4 kg/600.000).
- Rollback: patch `issue_cancel_credit_note` ném `RuntimeError` → đơn vẫn PAID/PROCESSING, kho không hoàn (AC5).
- Ma trận: `…/cancel/` chu/quan_ly 200, nv_kho/nv_giao/cskh 403, khách 401 và không có chứng từ; `/api/reports/batch|period`: chu 200, quan_ly/nv_kho/nv_giao/cskh 403, khách 401; dashboard chu/quan_ly/nv_kho 200, nv_giao/cskh 403, khách 401 (đếm đủ 3 lần 200).
- Không rò: quét order detail + `/api/guidance/order/<code>/` cho 5 Group (đếm 200 > 0) — không có `unit_cost`, không có khoá thuộc `COST_KEYS` (trừ `rate` là giá bán) ở quan_ly/nv_kho/nv_giao/cskh; AuditLog `issue_credit_note` không có khoá `COST_KEYS`, không có tên/SĐT/địa chỉ giả; `/api/audit-logs/` với quan_ly không có khoá giá vốn; dashboard cho quan_ly/nv_kho không có `unit_cost`/`cogs`.
- Append-only: chỉ có quyền `view_*`; Admin đăng ký nhưng `has_add/change/delete=False` kể cả superuser; `unit_cost` ẩn với người không có `inventory.view_costprice` ở `SalesCreditNoteLineAdmin` (`CostHidingMixin`) và ở inline trên trang chứng từ (chỉ đúng SAU sửa M1: inline phải override `get_fields`, xem mục "Sửa M1" cuối phần này; bản đầu của lô bị rò); test quét mã nguồn không tìm thấy `.update/.delete/.bulk_update` trên chứng từ.
- SR-14: dry-run không đổi số chứng từ/audit; `--apply` hai lần → lần 2 tạo 0; `issued_at` = audit mới nhất (kiểm khi có 2 dòng audit); không có audit → `order.created_at`, `stock_restored=True`; `stock_restored=False` lấy từ audit; output ở cả 3 lần chạy (dry-run, apply, apply lại) không chứa tên/SĐT/địa chỉ giả, `unit_cost`, giá vốn (110000/220000). Không chạy `--apply` ở DB nào ngoài DB test.
- Kỳ (SR-13 AC3): hoá đơn tháng 9 (đẩy về tháng 9 bằng `.update` trong test) huỷ tháng 10 → `period_pnl(9)` không đổi (revenue 300000, cogs 220000), `period_pnl(10)` có `credit_notes=300000`, `cogs_reversed=220000`, revenue = 150.000 − 300.000 (âm, đúng thiết kế). Phiếu hoàn REFUNDED của hoá đơn đã đảo → `refunds=0`; hoàn một phần của hoá đơn chưa đảo vẫn trừ 50.000.

### Điểm dừng
Không chạm điểm dừng nào: (a) `makemigrations` chỉ sinh 2 model + 1 index; (b) fixture `invoice.amount` = Σ dòng (300.000) nên test lô không lệch làm tròn; (c) không đổi tiền/giá vốn/quyền ngoài phạm vi story.

### Lệch thiết kế / giả định
1. **Sửa 3 test cũ ngoài danh sách file 02c** (không đổi hành vi, chỉ cập nhật kỳ vọng vì thêm khoá/model theo thiết kế): `reports/tests/test_api.py` + `test_services.py` (bộ khoá `batch_pnl` 16 → 18: thêm `reversed_qty`, `reversed_revenue`) — đường dẫn nằm trong `apps/reports/tests/` nên được phép; `sales/orders/tests/test_privacy_consent.py::test_gl03_ac7…` (danh sách model app `sales` cố định) thêm `SalesCreditNote`, `SalesCreditNoteLine` — **file này nằm ngoài danh sách 02c**, chỉ thêm 2 tên + chú thích; techlead xin xem lại.
2. Audit `issue_credit_note` được ghi cả khi lập bù (`backfilled: true` trong `changes`, actor = None) để có dấu vết; `issued_at` của chứng từ mới là thời điểm nghiệp vụ, còn `AuditLog.created_at` là lúc chạy lệnh.
3. `SalesCreditNote.amount = invoice.amount` (đã làm tròn BR-BH-15) và `period_pnl` dùng `amount`, còn `batch_pnl` dùng tổng `SalesCreditNoteLine.amount` (kg × giá). Khi hoá đơn có làm tròn hoặc combo hai số này có thể lệch nhau vài đồng; không đổi công thức.
4. `cogs_reversed` tính cho MỌI dòng chứng từ, kể cả `stock_restored=False` (hàng chưa về kho, đang ở người giao) — lô 🟡 trong ghi chú thiết kế; giá vốn của kg chưa hoàn kho vẫn được đảo. Cần Duy/techlead xác nhận ở Lô sau nếu muốn khác.
5. Dashboard chỉ trừ theo `issued_at__date=today` của chứng từ; không lọc theo trạng thái hoá đơn (chứng từ chỉ tồn tại cho hoá đơn ISSUED).
6. Batch/period lọc chứng từ theo `credit_note__sales_invoice__status=ISSUED` cho nhất quán với doanh thu gộp (hoá đơn đã CANCELLED không được tính hai chiều).

### Nợ / lưu ý cho QA
- Combo (BUNDLE): `SalesInvoiceLineBatch.qty` là kg thành phần còn `SalesInvoiceLine.rate` là giá cả combo, nên doanh thu lô theo công thức cũ `qty × rate` đã lệch cho combo; dòng chứng từ sao đúng công thức đó nên sau huỷ luôn về 0, nhưng bản thân số lệch của combo là nợ có sẵn, chưa sửa.
- Chưa chạy `backfill_credit_notes` trên staging/production — Duy chạy sau deploy: trước hết dry-run, đọc danh sách lô CLOSED bị ảnh hưởng rồi mới `--apply`.
- FE chưa hiển thị `reversed_qty/reversed_revenue`/`credit_notes` (không thuộc lô này).

### Sửa M1 (techlead review Lô 4) — Admin inline lộ `unit_cost`
Lỗi thật: `SalesCreditNoteLineInline` khai `fields` có `unit_cost` và `has_change_permission=False` nên Django đưa mọi field thành chỉ đọc; `CostHidingMixin` chỉ gỡ ở `readonly_fields`/`exclude` nên không ẩn được. Câu "Admin ẩn `unit_cost`" trong bản giao đầu của lô là sai (đã đính chính ở mục Bằng chứng). Sửa chỉ trong `backend/apps/sales/admin.py`: inline override `get_fields`, bỏ `cost_fields` khi user thiếu `inventory.view_costprice`. Không đụng `inventory/admin.py` (ngoài danh sách Lô 4; techlead gợi ý đưa `get_fields` vào `CostHidingMixin` sau, việc riêng).
- Test mới: `SR12CreditNoteTests.test_sr12_ac7_admin_an_unit_cost_voi_staff_thieu_view_costprice`. Staff chỉ có `view_salescreditnote` + `view_salescreditnoteline` (assert không có `view_costprice`) GET `/admin/sales/salescreditnote/<id>/change/` → assert **200**, có mã chứng từ (đúng trang), không có nhãn "Giá vốn ảnh chụp (đ/kg)" lẫn giá trị giả `123457,7777` (đặt bằng `.update` trong test); trang đổi và danh sách `salescreditnoteline` cũng 200 và không có; đối chứng user có `view_costprice` và superuser → 200, thấy nhãn và giá trị.
- ĐỎ (trước sửa): `AssertionError: 'Giá vốn ảnh chụp (đ/kg)' unexpectedly found in '<!DOCTYPE html>...` — trang 200, cột `column-unit_cost` và `<td class="field-unit_cost"><p>123457,7777</p>` hiện ra (đúng lý do, không phải 302/403).
- XANH (sau sửa): `manage.py test apps.sales.credit_notes.tests.test_p8_credit_note` → `Ran 17 tests ... OK`; toàn bộ `manage.py test` → `Ran 1328 tests in 55.465s ... OK`; `makemigrations --check --dry-run` → `No changes detected`.

### D1 phương án B — không sửa kỳ cũ (Duy quyết 30/09)
Vấn đề (techlead D1): hoàn một phần 50.000 xác nhận tháng 9 rồi huỷ đơn tháng 10 thì công thức đầu loại mọi phiếu hoàn của hoá đơn đã có chứng từ, làm lãi tháng 9 đổi từ 30.000 lên 80.000. Sửa `backend/apps/reports/services.py::period_pnl` (chỉ sửa hàm này + docstring, `batch_pnl`/dashboard không đổi, không phải sửa để nhất quán vì hai nơi đó không trừ phiếu hoàn):
- `refunds` kỳ: phiếu REFUNDED của hoá đơn có chứng từ chỉ bị loại khi `confirmed_at >= credit_note.issued_at`; xác nhận trước lúc huỷ vẫn trừ ở kỳ xác nhận của nó.
- Kỳ lập chứng từ: số đảo doanh thu (`credit_notes`) = `max(0, cn.amount − Σ phiếu REFUNDED của hoá đơn có confirmed_at < cn.issued_at)`. `cogs_reversed` giữ nguyên (mọi dòng chứng từ).
- Spec BR-HT-06 thêm câu quy tắc "(Duy quyết 30/09, phương án B)"; docstring `period_pnl`, module `reports/services.py`, `confirm_refund`, `reports/README.md` cập nhật.
- Test mới (`SR13D1PhuongAnBTests`, `apps/reports/tests/test_p8_pnl_credit_note.py`): (1) `ky_cu_khong_doi_ky_huy_dao_phan_con_lai`: `period_pnl(9)` trước huỷ == sau huỷ (so cả dict: refunds 50000, profit 30000); tháng 10 `credit_notes=250000`, `cogs_reversed=220000`, `refunds=0`, revenue −250000, profit −30000; tổng lãi 2 kỳ = 0 và (doanh thu − hoàn) 2 kỳ = 0; (2) không hoàn trước → như cũ (300000); (3) hoàn nốt 250.000 sau huỷ → không trừ hai lần (tháng 9 refunds 50000, tháng 10 refunds 0, credit_notes 250000); (4) đã hoàn đủ 300.000 trước huỷ → số đảo 0 (không âm), tháng 9 refunds 300000; (5) `backfill_credit_notes --apply` cho đơn có hoàn trước, `issued_at` lấy từ audit (tháng 10) → tháng 9 không đổi, tháng 10 `credit_notes=250000`.
- ĐỎ (trước sửa, `red_d1.txt`): `Ran 5 tests ... FAILED (failures=4)` — `period_pnl(9)` sau huỷ `refunds 0, profit 80000` khác trước huỷ `refunds 50000, profit 30000`; `Decimal('300000.00') != Decimal('0')`; `Decimal('0') != Decimal('50000')`; ca "không hoàn trước" xanh ngay (đúng: hành vi cũ giữ nguyên).
- XANH: `manage.py test apps.reports` → `Ran 38 tests ... OK`; toàn bộ `manage.py test` → `Ran 1333 tests in 57.608s ... OK`; `makemigrations --check --dry-run` → `No changes detected`.
- Lưu ý: nếu phiếu hoàn và chứng từ có cùng thời điểm (`confirmed_at == issued_at`) thì tính là "sau/cùng lúc" (bị loại khỏi refunds, không giảm số đảo). Cùng thời điểm chỉ xảy ra khi test ép giờ; thực tế phiếu hoàn xác nhận và huỷ là hai thao tác khác nhau.

### E1/E2 — báo cáo đã qua không được sửa số (Duy quyết 30/09) — **SR-14-AC2 đổi theo Duy 30/09**
Nguyên tắc Duy: "báo cáo đã qua thì không được sửa số".
- **E1** (`backfill_credit_notes --apply`): chứng từ lập bù có `issued_at = thời điểm chạy lệnh` (`timezone.now()` trong service, lệnh truyền `at=None`), KHÔNG lấy ngày AuditLog huỷ gốc; `backfilled=True`, `created_by=None`. `stock_restored` vẫn lấy từ AuditLog `cancel_paid_order` mới nhất (mặc định True). Kỳ cũ giữ nguyên; kỳ hiện tại nhận điều chỉnh, `period_pnl` (D1-B) tự trừ phần hoàn đã xác nhận trước đó. Đây là **thay đổi AC do Duy quyết**: SR-14-AC2 gốc ("`issued_at` = thời điểm AuditLog huỷ") không còn đúng; 02-stories.md không được sửa (ngoài quyền be-dev) — cần PO/điều phối cập nhật. Test AC2 cũ được viết lại (`test_sr14_ac2_apply_lap_chung_tu_issued_at_la_luc_chay_lenh_created_by_none`, `…khong_co_audit_van_issued_at_la_luc_chay_lenh`, `…stock_restored_lay_tu_audit_moi_nhat_khi_co_nhieu_dong`), ca (5) của D1 (`test_sr13_d1_backfill_ca_co_hoan_truoc`) đổi sang hoá đơn + hoàn ở tháng 8 để không phụ thuộc ngày chạy test.
- **E2** (`reports/services.py::batch_pnl`): lô `CLOSED` (có `closed_at`) chỉ trừ dòng chứng từ có `credit_note.issued_at <= batch.closed_at`. Chứng từ lập sau lúc chốt (kể cả lập bù) không đổi lãi lỗ lô, nhưng vẫn vào `period_pnl` kỳ hiện tại. Lô chưa chốt: như cũ. Giả định: lô `CLOSED` mà `closed_at` rỗng (chỉ xảy ra khi test ép trạng thái; `close_batch` luôn đặt `closed_at`) thì không lọc theo mốc chốt (trừ như cũ) — vì không xác định được mốc.
- Dry-run: thêm mục riêng "Lô đã CLOSED liên quan (lãi lỗ lô giữ nguyên, điều chỉnh vào kỳ hiện tại)" và từng dòng "đơn <mã> · lô <mã> — lãi lỗ lô giữ nguyên, điều chỉnh vào kỳ hiện tại"; chỉ mã đơn/mã lô, không PII/giá vốn (test kiểm sentinel).
- Spec: BR-HT-10 thêm câu về chứng từ lập bù; BR-BC-04 thêm vế "lô đã chốt: chỉ trừ chứng từ lập trước thời điểm chốt (Duy quyết 30/09)". Docstring lệnh, `batch_pnl`, README cập nhật. `period_pnl` và dashboard không đổi lần này.
- Test (`SR14E1E2BackfillReportTests` trong `apps/reports/tests/test_p8_pnl_credit_note.py` + `SR14E2DryRunTests`): (a) đơn huỷ tháng 8 (audit huỷ ép về tháng 8): `period_pnl(8)` trước/sau `--apply` bằng nhau mọi khoá, kỳ hiện tại `credit_notes=300000`, `cogs_reversed=220000`; (b) lô CLOSED: `batch_pnl` trước/sau `--apply` bằng nhau mọi khoá (revenue vẫn 300000 — đối chứng lỗi F04 cũ nằm nguyên trong số đã chốt), kỳ hiện tại vẫn có `credit_notes=300000`; (c) lô chưa chốt: `revenue 0, reversed_qty 2` như cũ; (d) luồng huỷ thường lô chưa chốt không đổi, huỷ thường trước khi chốt vẫn trừ sau khi chốt, huỷ SAU khi chốt qua luồng thường thì `batch_pnl` giữ nguyên nhưng kỳ hiện tại có chứng từ; (e) `--apply` hai lần → chứng từ không tăng, `issued_at` giữ nguyên; dry-run liệt kê riêng đơn thuộc lô CLOSED.
- ĐỎ (`red_e.txt`): `Ran 48 tests ... FAILED (failures=6)`: `issued_at` bằng ngày audit gốc `2026-09-01 not >= lúc chạy`; `batch_pnl` lô CLOSED sau `--apply` `qty_sold 0.000 != 2.000` (bị trừ); dry-run thiếu dòng "lãi lỗ lô giữ nguyên, điều chỉnh vào kỳ hiện tại". Lưu ý: ca (a) và D1-5 (đổi sang tháng 8) đã xanh sẵn ở lần chạy đầu vì hệ thống thời điểm chạy test trùng tháng của audit; ca (a) sau đó được ép audit về tháng 8 để phân biệt được hai hành vi.
- XANH: `apps.reports apps.sales` → `Ran 395 tests ... OK`; toàn bộ `manage.py test` → `Ran 1341 tests in 56.459s ... OK` (chạy sau khi sửa xong docstring/README/spec); `makemigrations --check --dry-run` → `No changes detected`.

**T1 (techlead vòng 2):** `apps/reports/tests/test_p8_pnl_credit_note.py` đổi 4 chỗ lấy year/month từ `timezone.now()` (UTC) sang `timezone.localdate()` (giờ VN, khớp bộ lọc của `period_pnl`), tránh đỏ 00:00-07:00 VN ngày 1 hằng tháng. Kiểm bằng script tạm (scratchpad, ngoài repo) patch `timezone.now` = 2026-10-31 20:00 UTC (= 01/11 03:00 VN): 48 test P8 (reports + credit_notes) OK; với mẫu cũ thì 3 test đỏ. Các file test P8 khác chỉ dùng `now()` cho so sánh thời điểm, không lấy year/month.

## Lô 5 — BE

Story: SR-15 (chốt lô Quá hạn phải xử lý hết tồn, BR-LO-04/07), SR-16 (trả NCC, BR-MH-08), SR-17 (dashboard bỏ dữ liệu khách), F11 (`expired_qty`). Quy tắc Duy 30/09: lô đã chốt / kỳ đã qua không đổi số; logic Lô 4 trong `batch_pnl` (lô CLOSED chỉ trừ chứng từ trước `closed_at`) giữ nguyên.

### File đã sửa
- `backend/apps/inventory/models/supplier_returns.py` (mới), `models/__init__.py` (re-export), `models/stock.py` (`MovementType.SUPPLIER_RETURN`).
- `backend/apps/inventory/migrations/0004_batchsupplierreturn.py` (mới, xem dưới).
- `backend/apps/inventory/batches/services.py`: `check_close_batch` (bỏ ngoại lệ EXPIRED/CANCELLED; đếm đơn mở qua `_open_orders_count` — techlead L3), `_check_expired_reserved` (tách từ SR-08), `check_cancel_expired_batch`, `check_process_expired_stock` (mới), `cancel_expired_batch(confirm_qty=None)`, `return_batch_to_supplier` (mới).
- `backend/apps/inventory/batches/api.py`, `serializers.py` (`CancelExpiredInput`, `ReturnToSupplierInput`), `next_steps.py`.
- `backend/apps/delivery/attention_api.py`, `backend/apps/reports/services.py` (`batch_pnl`), `backend/apps/reports/dashboard_api.py`.
- Test mới: `backend/apps/inventory/batches/tests/test_p8_lo5_expired_return.py` (50 test), `backend/apps/reports/tests/test_p8_lo5_pnl_dashboard.py` (13 test).
- Doc: `doc/business-process-spec.md` chỉ BR-LO-04 (sửa), BR-LO-07 (mới), BR-MH-08 (mới), BR-BC-04 (thêm vế NCC), E-10, theo 02b §5.6.
- Không sửa: `cost_keys.py` (Lô 1 đã có `supplier_refund_amount`, `supplier_return_cost`), `admin.py` (không đăng ký `BatchSupplierReturn` vào Admin: không có màn hình nào lộ tiền hoàn), `landed_unit_cost`/`recompute_landed_cost`, `period_pnl`, `cancel_receipt`, không quyền/migration Group mới.

### Migration `inventory/0004_batchsupplierreturn.py`
Đúng 2 operation: `AlterField(stockledgerentry.movement_type)` (thêm choice `SUPPLIER_RETURN`, `max_length` 16 giữ nguyên) + `CreateModel(BatchSupplierReturn)` (`default_permissions=("view",)`). Đã đọc lại file. `sqlmigrate inventory 0004`: AlterField là `(no-op)`, CreateModel = 1 `CREATE TABLE` + 2 `CREATE INDEX` (batch_id, created_by_id) + `request_id ... UNIQUE`. `migrate` sạch trên SQLite ở scratchpad (`DATABASE_URL=sqlite:///.../scratchpad/lo5/clean.sqlite3`) → rollback `migrate inventory 0003` (`Unapplying inventory.0004... OK`) → `migrate inventory` lại OK. Không đụng `backend/db.sqlite3`. `makemigrations --check --dry-run` → `No changes detected`.

### Contract thực tế (cho FE)
```
POST /api/inventory/batches/<pk|batch_id>/return-to-supplier/     Chủ (inventory.cancel_expired_batch)
Request  {"qty": "3.000", "supplier_refund_amount": "150000", "note": "", "request_id": "<uuid>"}
         qty, supplier_refund_amount, note nhận chuỗi/số; supplier_refund_amount và note tuỳ chọn (mặc định 0 / ""); qty và request_id bắt buộc có khoá.
200      {"batch_id": "LO-…", "status": "EXPIRED", "qty_available": "2.000", "returned_qty": "3.000", "return_id": 12}
         KHÔNG có tiền NCC hoàn. request_id trùng -> 200 cùng dạng, không trừ kho lần 2.
400      {"code": "BR-MH-08", "detail": "Số kg trả phải lớn hơn 0 và không vượt tồn 5,000 kg."}   (qty <=0/rác/NaN/vượt tồn/quá 3 số lẻ)
400      {"code": "BR-MH-08", "detail": "Tiền NCC hoàn phải là số không âm, tối đa 2 chữ số thập phân."}
400      {"code": "BR-MH-08", "detail": "Ghi chú không được chứa dãy số dài (số điện thoại, số tài khoản)."}   / "Ghi chú tối đa 500 ký tự."
400      {"code": "BR-LO-07", "detail": "Chỉ xác nhận trả NCC cho lô Quá hạn còn tồn."}   (không EXPIRED hoặc tồn 0)
400      {"code": "BR-LO-07", "detail": "Còn 2,000 kg đang giữ chỗ của 1 đơn — chờ đơn thanh toán hoặc hết hạn giữ chỗ rồi huỷ."}
400      {"code": "BR-LO-05", "detail": "Lô đã chốt."}
400 (DRF) thiếu khoá `qty` hoặc `request_id` hợp lệ (UUID) -> lỗi field chuẩn DRF (không có `code`).
403 quan_ly/nv_kho/nv_giao/cskh · 401 chưa đăng nhập · 404 lô không có.

POST /api/inventory/batches/<pk>/cancel-expired/   body TUỲ CHỌN {"confirm_qty": "100.000"}; response không đổi (BatchSerializer)
400  {"code": "BR-LO-07", "detail": "Tồn đã đổi (70,000 kg) — tải lại."}     (confirm_qty != tồn hiện tại)
400  {"code": "BR-LO-07", "detail": "Số kg xác nhận không hợp lệ."}          (confirm_qty rác)
     Không gửi body -> hành vi cũ (DW-06). Huỷ lô tồn 0 (đã trả hết NCC) vẫn hợp lệ.

GET /api/dashboard/attention/   thêm "expired_batches_open": <số lô EXPIRED còn tồn> cho user có inventory.cancel_expired_batch (Chủ).
    403 chỉ khi thiếu cả 4 quyền (confirm_with_customer, decide_unconfirmed, print_label, cancel_expired_batch).
    quan_ly không có khoá này. User chỉ có cancel_expired_batch nhận {"expired_batches_open": n}.

GET /api/guidance/batch/<id>/  (lô EXPIRED): next_steps
    cancel_expired  label "Xác nhận Đã huỷ phần tồn"  command inventory.batch.cancel_expired
    return_to_supplier label "Xác nhận Đã trả NCC"    command inventory.batch.return_to_supplier  (chỉ khi qty_available > 0)
    close  label "Chốt lô": HIỆN cả khi EXPIRED; allowed=false + missing BR-LO-04 khi còn tồn; allowed khi tồn 0 và đủ điều kiện khác.
    Còn giữ chỗ: cả 2 bước xử lý tồn allowed=false, missing BR-LO-07 "Còn X kg đang giữ chỗ của N đơn — …".

GET /api/reports/batch/<batch_id>/  (view_profitreport): thêm "supplier_return_qty", "supplier_refund_amount" (20 khoá); total_cost = purchase_cost + allocated_cost − supplier_refund_amount.
GET /api/dashboard/summary/: recent_orders[] còn đúng {code, amount, status, status_label, expires_at}.
```
AI: lệnh `inventory.batch.return_to_supplier` có `max_level="C"` và `force_c=True` (quyền `cancel_expired_batch` thuộc `FORCE_C_PERMS`); `cancel_expired` vẫn form_only như cũ (không gắn input_serializer vào decorator để không đổi registry).

### Rule BR đã cài
- BR-LO-04: `check_close_batch` — mọi lô còn `qty_available > 0` bị chặn, kể cả EXPIRED (gỡ ngoại lệ S04). Chuỗi đếm đơn mở dùng `_open_orders_count(batch, OPEN_ORDER_STATUSES)`; câu chữ giữ nguyên "Còn N đơn đang mở …".
- BR-LO-07: `check_process_expired_stock` (EXPIRED? / đã chốt BR-LO-05 / tồn > 0 / còn giữ chỗ), `confirm_qty` khớp tồn.
- BR-MH-08: `return_batch_to_supplier` — khoá dòng lô, `request_id` idempotent (kiểm sau khi khoá; `request_id` đã dùng cho lô khác -> 400 BR-MH-08), 0 < qty ≤ tồn và ≤ 3 số lẻ, tiền ≥ 0 và ≤ 2 số lẻ, ghi chú ≤ 500 ký tự và chặn `has_long_digit_run`, ghi `BatchSupplierReturn` + `SUPPLIER_RETURN` (âm) + AuditLog. Lô vẫn EXPIRED.
- BR-BC-04: `batch_pnl` + `supplier_return_qty`, `supplier_refund_amount`; `total_cost` trừ tiền hoàn; không tính lại `landed_unit_cost`; `period_pnl` không đổi.
- F11: `expired_qty` chỉ đếm `WRITE_OFF` có `reference` bắt đầu `"cancel_expired_batch "` (huỷ phiếu nhập DW-18 và hàng hoàn huỷ không còn bị tính là quá hạn).

### Chống rò
- Response trả NCC, 400, 403 không chứa tiền hoàn (test dò chuỗi sentinel `1234567`).
- AuditLog: `changes = {qty, supplier_refund_amount}`; `supplier_refund_amount` thuộc `COST_KEYS` nên quan_ly không thấy; `note` audit chỉ là `return_batch_to_supplier <n>kg`, không có ghi chú tự do lẫn tiền. Test quét hết các trang `/api/audit-logs/` với quan_ly: `ok_responses > 0`, thấy action `return_batch_to_supplier`, không còn khoá COST_KEYS, không có chuỗi `1234567`; Chủ thấy đủ.
- `BatchSerializer` không thêm field nào (test: không có khoá chứa `refund`/`supplier_return`, nv_kho không thấy `purchase_rate`/`landed_unit_cost`).
- SR-17: dashboard `recent_orders` bỏ `customer`, `phone_last4` và `select_related("customer")`, không phân nhánh theo nhóm. Test: đúng 5 khoá cho chu/quan_ly/nv_kho; JSON không chứa tên giả, `0456`, SĐT, địa chỉ, `phone_last4`, `customer`; nv_giao/cskh 403, khách 401. Fixture chỉ dùng tên, SĐT (`0900000456`), địa chỉ giả.

### TDD đỏ → xanh
- ĐỎ (trước code, `scratchpad/lo5/red.txt`): `apps.inventory.batches.tests.test_p8_lo5_expired_return` không nạp được (`ImportError: cannot import name 'BatchSupplierReturn'`); `apps.reports.tests.test_p8_lo5_pnl_dashboard` → `Ran 14 tests ... FAILED (failures=8, errors=7)`. Lý do đúng: `recent_orders` còn `"customer":"Khách Giả Bảy","phone_last4":"0456"`; `batch_pnl` thiếu `supplier_return_qty`/`return_batch_to_supplier` chưa có.
- XANH: `manage.py test apps.inventory.batches.tests.test_p8_lo5_expired_return apps.reports.tests.test_p8_lo5_pnl_dashboard` → `Ran 63 tests ... OK`.
- Toàn bộ: `DJANGO_DEBUG=1 env -u DATABASE_URL manage.py test` → trước 1379 OK; sau `Ran 1442 tests in 65.513s ... OK` (+63 test mới, 0 failure, 0 xoá); `makemigrations --check --dry-run` → `No changes detected`.
- Bổ sung sau review techlead (T5-1, T5-2): thêm 5 test vào `test_p8_lo5_expired_return.py` (lớp `SR15AiFloorTests` 4 test: luật sàn AI, đối chứng tồn 0, lệnh AI qua API hạ C, job `run_due_ai_actions` ESCALATED; và `test_sr16_ac3_request_id_da_dung_cho_lo_khac_400_br_mh_08`). File này 55 test; toàn bộ `Ran 1447 tests ... OK`; `makemigrations --check --dry-run` → `No changes detected`.
- Lượt chạy đầu sau khi code có 6 đỏ (test cũ, xem "Lệch thiết kế"), đã cập nhật kỳ vọng rồi chạy lại xanh.

### Lệch thiết kế / cần Duy-techlead xác nhận
1. **Test S04 cũ**: không tồn tại test S04 nào cho phép chốt lô EXPIRED còn tồn (`test_l1_close_batch.py` không có ca EXPIRED). Việc bỏ ngoại lệ ở `check_close_batch` không làm đỏ test cũ nào ở tầng service/AI (`test_dw25_close_batch`, `test_p8_close_batch_sold` xanh). Điểm dừng "test cũ đỏ vì bỏ ngoại lệ" KHÔNG bị chạm theo nghĩa chặt.
2. **Test cũ cập nhật kỳ vọng vì thêm hợp đồng mới theo 02b** (không đổi hành vi khác), 6 test, trong đó 3 nằm NGOÀI danh sách file 02c Lô 5 — cần người duyệt xác nhận:
   - Trong `inventory/batches/tests/` (thư mục được phép): `test_cancel_expired.py::test_dw06_ac6_guidance_next_steps_expired_then_cancelled` — nhãn "Huỷ lô" → "Xác nhận Đã huỷ phần tồn" và dòng `assertNotIn("close", steps_before)` → `close` hiện, `allowed=false`, có BR-LO-04 (do bỏ điều kiện `status != EXPIRED` ở bước 4, đúng 02b §5.3). Đây là test gần nhất với việc bỏ ngoại lệ ở tầng Tiếp theo; báo rõ để techlead xem có coi là "chạm điểm dừng" không.
   - Trong `reports/tests/` (được phép): `test_api.py::test_chu_can_view_batch_pnl`, `test_services.py::test_batch_pnl_keys_unchanged` — bộ khoá 18 → 20.
   - NGOÀI danh sách: `ai/registry/tests/test_discipline.py` (số `@action` 23 → 24), `ai/registry/tests/snapshots/commands_index_snapshot.json` (thêm `inventory.batch.return_to_supplier`), `delivery/tests/test_cskh_l4.py::test_cs15_ac1_owner_sees_all_6_keys` (thêm `expired_batches_open`). Đều là hệ quả trực tiếp của action/khoá mới theo thiết kế, sửa mang tính cơ học.
3. Serializer đầu vào để `qty`/`supplier_refund_amount`/`note` dạng chuỗi lỏng (không `DecimalField`) để mọi giá trị sai trả 400 `BR-MH-08` thống nhất thay vì lỗi field DRF. Hệ quả: schema AI của lệnh này mô tả các trường là chuỗi.
4. `return_batch_to_supplier` tuân thủ 02b nhưng chặn thêm số lẻ vượt 3 (kg) / 2 (tiền) bằng BR-MH-08, và tiền ≥ 10^12 (giới hạn cột `max_digits=14`) để không 500.
5. Trả NCC luôn từ chối lô CLOSED (BR-LO-05) nên `batch_pnl` không cần lọc `closed_at` cho phần NCC; số lô đã chốt không đổi.

### Nợ / lưu ý
- `apps/inventory/batches/timeline.py` (ngoài danh sách): `SUPPLIER_RETURN` rơi vào nhãn chung "Biến động kho X kg"; nên thêm nhãn "Trả NCC" ở lô sau. Sổ chi tiết không lộ tiền.
- `apps/ai/execution/safety.py` docstring còn nhắc "tồn = 0 hoặc EXPIRED/CANCELLED" (ngoài danh sách); logic dùng lại `check_close_batch` nên tự đúng, chỉ cần sửa câu chữ.
- `period_pnl` chưa phản ánh tiền NCC hoàn (đúng 02b §5.5: "để sau").
- FE: `BatchDetailSheet` phải gửi `confirm_qty` = tồn đang hiển thị và sinh `request_id = crypto.randomUUID()` khi mở form trả NCC; xử lý 400 BR-LO-07 "Tồn đã đổi" bằng nút Tải lại.

### B1 — Admin Nhật ký lộ `changes` (QA Critical, đã sửa)
- **Lệch thiết kế (điều phối cho phép):** sửa `backend/apps/accounts/admin.py` (ngoài danh sách 02c) vì lỗi chặn SR-16-AC6. Lỗi có từ trước Lô 5 (khoá `purchase_rate`...), Lô 5 thêm khoá `supplier_refund_amount` vào.
- `AuditLogAdmin`: `exclude = ("changes",)` + readonly callable `changes_visible` (tạo theo request trong `get_readonly_fields`, không lưu trạng thái trên instance admin). Dùng đúng `can_view_cost` và `redact_cost` từ `apps.common.cost_keys` như `/api/audit-logs/` (một nguồn duy nhất). Người xem thiếu `inventory.view_costprice` thấy `changes` đã bỏ mọi khoá COST_KEYS; Chủ/superuser thấy đủ. `list_display`, `search_fields` không chứa `changes`, không có action export. `note` giữ nguyên (quy ước audit.py: không ghi tiền; API cũng trả nguyên văn).
- Bài học M1 Lô 4: field readonly tường minh không qua `CostHidingMixin` nên kiểm bằng HTML thật (status 200), không tin cấu hình.
- Test (`inventory/batches/tests/test_p8_lo5_qa_edges.py`): bỏ `@expectedFailure` ở `QaLeakTests.test_qa_admin_html_khong_lo_tien_ncc_...`; `QaAdminAuditBaselineTests` đổi thành 2 test: staff `quan_ly` không thấy `purchase_rate`/`7654321`/`supplier_refund_amount`/tiền NCC (khoá không nhạy cảm `status` vẫn hiện), và đối chứng Chủ (is_staff) + superuser vẫn thấy đủ. Đã thử tạm đặt `show_cost = True`: 2 test đỏ, khôi phục thì xanh.
- Toàn bộ `manage.py test`: `Ran 1493 tests in 106.089s ... OK` (0 expected failure); `makemigrations --check --dry-run` -> `No changes detected`.

## Lô 5 — FE

Phạm vi: SR-15 (AC3, AC4, AC7), SR-16 (AC8), SR-17 (AC3). Chỉ sửa `erp-console/`. Không commit, không deploy.

### Đã làm (đường dẫn dưới `erp-console/`)
- **Lô quá hạn còn tồn** (`features/inventory/`):
  - `components/BatchDetailSheet.tsx`: vẽ nút từ `next_steps`. Lô EXPIRED còn tồn có 2 nút "Xác nhận Đã huỷ phần tồn" và "Xác nhận Đã trả NCC". Nút "Chốt lô" luôn hiện và bị khoá kèm lý do (BR-LO-04) khi còn tồn. Lô còn giữ chỗ thì 2 nút xử lý tồn cũng bị khoá kèm lý do BR-LO-07. Không có quyền (BR-PQ-12) thì không hiện nút.
  - Huỷ phần tồn: hộp thoại nêu đúng số kg đang hiển thị, gửi `confirm_qty` bằng đúng số đó. 400 BR-LO-07 hiện `detail` tiếng Việt kèm nút "Tải lại".
  - `components/ReturnToSupplierDialog.tsx` (mới): ô kg `inputMode="decimal"` (nhận "," hoặc ".", tối đa 3 số lẻ, có nút "Trả hết"), tiền NCC hoàn tuỳ chọn (chỉ số), ghi chú. `request_id` sinh 1 lần khi mở form. Chặn bấm đúp (ref + nút khoá). Hiện `detail` của 400. Sau khi lưu KHÔNG hiện tiền hoàn ở đâu cả.
  - `components/ModalDialog.tsx` (mới): hộp thoại bẫy Tab, Esc chỉ đóng hộp thoại con (không đóng SideSheet), khoá đóng khi đang gửi.
  - `components/InventoryScreen.tsx`: đọc `?status=` (danh sách trắng), bọc `Suspense`. Chế độ lọc: tiêu đề "Lô quá hạn còn tồn", chip "Bỏ lọc, xem tất cả lô", ẩn cột NCC/Kho, có trạng thái rỗng.
  - `api.ts`: `getBatchesByStatus`, `cancelExpiredBatch(batchId, confirmQty?)`, `returnToSupplier(batchId, input)`, `closeBatch(batchId)`, `batchStatusLabel`, `decimalKg`. `types.ts`: `ReturnToSupplierInput`, `ReturnToSupplierResult`, `BatchApiRow`, `BatchActionResult`.
  - `mock.ts`: 3 lô quá hạn bịa (L0908-CT00, L0909-MU00 có giữ chỗ 1,5 kg, L0910-TS00), trạng thái trong bộ nhớ. Công cụ DevTools: `__caveMock.expiredSetQty(id, qty)`, `expiredState()`, `expiredReset()`.
  - `inventory.module.css`: bỏ hex/rgba, dùng token.
- **Tổng quan** (`features/overview/`): bỏ cột "Khách" và `o.customer` khỏi `matches`; thêm thẻ Cần chú ý "Lô quá hạn còn tồn: N" (`expired_batches_open`) trỏ `/inventory/?status=EXPIRED`; `types.ts` thêm `expired_batches_open?: number`; `mock.ts` chỉ trả cho Chủ; `overview.test.ts` cập nhật (quan_ly / cskh / nv_kho không có khoá, Chủ = 3, 403 cho nv_giao, `recent_orders` không có tên/SĐT). Hex inline trong `AttentionBlock.tsx` đổi sang token.
- `e2e/p8_lo5_fe_lo_qua_han.py` (mới): Playwright Python.
- README của `features/inventory` và `features/overview` đã cập nhật.

### Ngoại lệ phạm vi (ngoài thư mục được phép, cần Duy/techlead biết)
1. `shared/lib/dashboardSummary.ts`: bỏ `customer`, `phone_last4` khỏi `RecentOrder` (khớp BE: `recent_orders[]` = `{code, amount, status, status_label, expires_at}`).
2. `shared/lib/dashboardSummary.mock.ts`: bỏ hết tên khách và SĐT giả trong seed.
3. `features/guidance/mock.ts`: nhánh `batch` gọi `mockExpiredBatchGuidance` (guidance của lô quá hạn nằm ở mock inventory).

### Kiểm chứng (đã chạy trong lượt này)
- `npx tsc --noEmit` → sạch.
- `npm run build` (bản thật, không mock) → thành công. `grep -rl "expiredSetQty\|L0908-CT00\|Ghe Tư Hải" out` → không có file nào (mock không lọt vào bản thật). Lần build đầu có lọt do hằng `MOCK` trong `api.ts` làm bundler không cắt được nhánh mock; đã đổi sang `process.env.NEXT_PUBLIC_USE_MOCK === "1"` trực tiếp.
- `npm test` → 10 file, 103 test qua.
- Playwright (bản build mock, cổng 3215, 1366px và 375px, Chủ và kho1): **77/77 PASS** ở lần chạy trước khi đổi mã lỗi ghi chú (xem "Đối chiếu contract"). Cách chạy: build mock (`NEXT_PUBLIC_USE_MOCK=1 npm run build`), `python3 -m http.server 3215 --bind 127.0.0.1` trong `out/`, rồi `BASE=http://127.0.0.1:3215 SHOTS=<thư mục> python3 e2e/p8_lo5_fe_lo_qua_han.py`. Sau khi xong phải build lại bản thật (không để mock trong `out/`).
- Ảnh (22 file) ở `doc/features/2026-09-30-sua-loi-review/qa-lo5/` (`lo5-1366-1..11`, `lo5-375-1..11`).
- Luồng đã chạy thật: thẻ "Lô quá hạn còn tồn: 3" → danh sách lọc 3 lô; mở lô thấy 2 nút bật + Chốt khoá lý do; form trả NCC chặn kg vượt tồn phía máy khách; 400 tồn đổi hiện detail + "Tải lại tồn"; "Trả hết" + bấm đúp chỉ gửi đúng 1 request; tiền hoàn 150.000 không hiện sau khi lưu; Chốt mở sau khi tồn về 0; huỷ phần tồn gửi `confirm_qty`, lệch → 400 "Tồn đã đổi (5,000 kg) — tải lại."; lô giữ chỗ khoá cả 3 nút; kho1 không thấy thẻ/nút; Tổng quan không còn cột Khách, không tên khách trong DOM, không cuộn ngang ở 375px.

### Đối chiếu contract BE thực tế (điều phối gửi giữa chừng)
- Khớp: URL, body/response của `return-to-supplier` và `cancel-expired`, 400 `{code,detail}`, `expired_batches_open` ở `/api/dashboard/attention/`, nhãn bước, `close` luôn hiện + BR-LO-04, giữ chỗ → BR-LO-07, `recent_orders` 5 khoá.
- Đã sửa: mock trả ghi chú có dãy số dài bằng code `BR-MH-08` (trước đó tôi đoán `NOTE_LONG_DIGITS`). FE không rẽ nhánh theo code này. Thay đổi chỉ là chuỗi trong mock; chưa chạy lại Playwright sau thay đổi này, `tsc` và `npm test` chạy lại xanh.
- Còn đoán: 400 DRF thiếu khoá (không có `code`) — FE vẫn hiện thông điệp của `ApiError`, chưa thử với dạng `{"qty":["..."]}` thật. Nút "Tải lại tồn" hiện cho mọi BR-MH-08, kể cả lỗi ghi chú/tiền (vô hại nhưng thừa).

### Nợ / lưu ý
- Danh sách lọc EXPIRED dùng `GET /api/inventory/batches/?status=EXPIRED` chỉ trang 1 (50 dòng), lọc `qty_available>0` phía FE. `BatchSerializer` chỉ trả id nên cột mặt hàng hiện `item_code`, bỏ cột NCC/Kho. Đề nghị BE thêm `item_name`, `supplier_name`, `warehouse_name`, `status_label`, hoặc đưa lô EXPIRED còn tồn vào summary.
- Lỗi có sẵn ngoài phạm vi: `shared/ui/globals.css` (mobile) luật `table.data tbody tr:last-child td` mạnh hơn `td.m-title`/`m-fig`/`m-status` nên dòng cuối mọi bảng ở 375px lệch bố cục (thấy ở `lo5-375-2`, dòng L0910-TS00).
- Chưa chạy lại các script e2e cũ (`e2e/s8_views.py` v.v.); grep tên khách trong e2e không thấy phụ thuộc cột "Khách".
- Console có nhiễu "Failed to fetch RSC payload" do `python3 -m http.server` không phục vụ prefetch RSC của Next; không liên quan thay đổi này, không có SĐT trong log.
- Nhãn `close` "Chốt lô" và mã bước (`cancel_expired`, `return_to_supplier`, `close`) là theo mock/giả định; nếu BE dùng khoá khác thì `BatchDetailSheet` cần đổi map.

### M5-1 — mock lọt vào bản build thật (techlead, Duy duyệt gộp Lô 5)
- **Nguyên nhân:** hằng `USE_MOCK` được `export` từ file khác rồi `import` sang; bundler không cắt được nhánh mock khi hằng đi qua ranh giới module. Chỉ khi viết thẳng `process.env.NEXT_PUBLIC_USE_MOCK === "1"` tại chỗ dùng thì Next thay bằng literal và cắt nhánh chết.
- **erp-console:** `features/catalog/api.ts` (dòng 5, 28, 47) bỏ import `USE_MOCK`, viết thẳng biểu thức. `shared/lib/http.ts` giữ nguyên (dùng nội bộ cùng file, không ảnh hưởng bundle). Rà toàn bộ `erp-console/`: mọi file khác đã viết thẳng hoặc dùng hằng cục bộ trong cùng file; không còn chỗ import `USE_MOCK`.
- **frontend/ (cùng mẫu, có lọt thật):** bản thật chứa `mockSiteInfo` (SĐT giả `0900000000`) trong `app/layout`, `shop/checkout`, `shop/orders`. Đã viết thẳng biểu thức ở `features/site/api.ts`, `features/content/api.ts`, `features/checkout/components/{CheckoutScreen,PaymentPanel,OrderPaymentPanel}.tsx`, `lib/api.ts`; bỏ import `USE_MOCK` ở các file đó. `lib/api.ts` vẫn `export USE_MOCK` (không còn nơi nào import).
- **Trùng khớp giả (không phải mock):** `erp-console/features/cskh/CskhCallModal.tsx:410` có placeholder `VD: 0900000456` làm grep `0900000` dính ở `/cskh/`. Đổi thành `VD: 09xx xxx xxx` (số giả trông như thật cũng không nên nằm trong bundle).
- **Kiểm (chạy trong lượt này, build với `NEXT_PUBLIC_USE_MOCK=0` truyền trực tiếp):**
  - erp-console: `npx tsc --noEmit` sạch; `npm test` 10 file / 103 test qua; `npm run build` OK; `grep -rlE "demo1234|0900000|Khách Giả|mockGet" out/` → 0 file; `grep -rlE "expiredSetQty|L0908-CT00|__caveMock" out/` → 0 file.
  - frontend: `npx tsc --noEmit` sạch; `npm run build` OK; `grep -rlE "demo1234|0900000|Khách Giả|mockGet" out/` → 0 file (trước sửa: 3 file). `frontend/` không có script `npm test`.
  - Trước sửa, cùng grep ở erp-console ra `out/_next/static/chunks/2800-*.js` (theo techlead) — sau khi build lại và sửa thì không còn.
- `out/` của cả hai đang là bản thật. Chưa chạy lại Playwright mock cho `frontend/` sau đổi này (đổi chỉ là cách viết điều kiện, ngữ nghĩa giữ nguyên; tsc sạch).

## Lô 6 — BE

Phạm vi: SR-18 (F1 IDOR ảnh khi tạo/sửa bài CMS, BR-ND-07). Không migration, không đổi model, không đổi contract API (chỉ thêm ca 400 BR-ND-07). Không commit.

### File đã sửa (dưới `backend/apps/content/`)
- `entries/services.py`: `save_draft` — khối "Cover image" viết lại; thêm hàm `_as_pk`. Import `MSG_IMAGE_AFTER_FIRST_SAVE`.
- `body/sanitize.py`: hằng `MSG_IMAGE_AFTER_FIRST_SAVE = "Tải ảnh sau khi lưu nháp lần đầu."`; nhánh khối `image` ở chế độ `strict` chặn khi `entry is None`.
- `public/serializers.py`: `_own_cover(version)` (bìa chỉ hiện nếu `cover.entry_id == version.entry_id`); `public_body` lọc ảnh `entry_id=version.entry_id`; hai serializer chi tiết/danh sách dùng `_own_cover`.
- Test mới: `entries/tests/test_p8_sr18_image_idor.py` (19 test), `public/tests/test_p8_sr18_public.py` (4 test); thêm lớp `Sr18SanitizeCreateTests` (3 test) vào `body/tests/test_sanitize.py`. Không sửa/xoá test cũ.

### Nguyên nhân gốc
`save_draft` kiểm sở hữu bằng `if entry and not ContentImage...exists()`: khi tạo (`entry=None`) điều kiện đoản mạch nên bỏ qua kiểm tra; sau đó `ContentImage.objects.get(pk=cov_id)` lấy ảnh của bất kỳ bài nào. `normalize_body` cũng chỉ kiểm khi `entry is not None`. Lớp 1b `public_body` lấy ảnh theo `pk` không kiểm bài, và lấy `alt` của ảnh đó, nên bài đã đăng có dữ liệu cũ trỏ ảnh bài khác (kể cả bài nháp) sẽ lộ ảnh + alt.

### Đỏ → xanh
Đỏ (trước khi sửa, `manage.py test apps.content`, 132 test, 8 fail; các fail còn lại là ca đã đúng sẵn):
- `Sr18CreateTests.test_sr18_ac1_tao_bai_voi_cover_cua_bai_khac_400` — `AssertionError: 201 != 400` (đúng repro A5-f1, bài mới tạo với `cover_image` của bài A).
- `Sr18CreateTests.test_sr18_ac1_tao_bai_voi_khoi_image_cua_bai_khac_400` — `201 != 400`.
- `Sr18CreateTests.test_sr18_ac1_khi_tao_moi_moi_anh_deu_bi_chan_...` — `'Ảnh bìa không tồn tại (BR-ND-07).' != 'Tải ảnh sau khi lưu nháp lần đầu.'`.
- `Sr18GroupMatrixTests.test_sr18_chu_cung_bi_chan_anh_bai_khac` — `201 != 400`.
- `Sr18SanitizeCreateTests.test_sr18_ac1_entry_none_khoi_image_strict_raise` — `BusinessError not raised`.
- `Sr18PublicLayer1bTests` 3 test — `cover_image` là dict (ảnh nháp bài A, `alt` "Ảnh nháp bài A") `is not None`; body công khai chứa `content/<id A>/...` (rò ảnh nháp của bài khác).
Xanh sau khi sửa: `manage.py test apps.content` 132 OK; thêm 1 test `cover_image` kiểu lạ ("abc", True, -1, list, dict) -> 400 chứ không 500: `apps.content.entries` 30 test OK.

Toàn bộ: `DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test` → `Ran 1523 tests in 111.150s ... OK` (1497 cũ + 26 mới: 19 + 4 + 3). `makemigrations --check --dry-run` → `No changes detected`.

### Hành vi thực tế (contract lỗi cho FE)
Mọi ca là `400 {"detail": <thông điệp>, "code": "BR-ND-07"}`:
| Tình huống | detail |
|---|---|
| `POST /api/content/entries/` có `cover_image` (mọi giá trị truthy) hoặc khối `image` hợp lệ về kiểu | `Tải ảnh sau khi lưu nháp lần đầu.` (không tạo bài) |
| `PATCH` `cover_image` không thuộc bài (ảnh bài khác, không tồn tại, kiểu lạ) | `Ảnh bìa không thuộc bài viết này (BR-ND-07).` |
| `PATCH` khối `image` không thuộc bài | `Ảnh không thuộc bài viết này (BR-ND-07).` |
| Vượt 20 ảnh/bài (cover + khối, đếm ảnh khác nhau) | `Vượt quá số lượng ảnh tối đa cho phép (BR-ND-07).` (như cũ) |
Ảnh không tồn tại và ảnh bài khác dùng chung một thông điệp, không lộ ảnh có tồn tại hay không, không có alt/URL của ảnh bài khác. Khối `image` thiếu `image_id` số nguyên vẫn bị bỏ im lặng như cũ (không lỗi). FE: màn soạn chỉ cho tải/chèn ảnh sau khi bài có `id`; nếu vẫn nhận 400 này khi tạo thì hiện `detail`.

Ma trận Group (POST/PATCH): `chu` 201/200, `quan_ly` 201/200, `nv_kho`/`nv_giao`/`cskh` 403, khách 401 (dữ liệu không đổi). Ảnh bài khác của người không có quyền vẫn là 403, không lộ BR-ND-07.

### Ca ngoài đường thuận đã có test
Ảnh mồ côi đã gỡ khỏi cover/body của bài B dùng lại được (200); ảnh thuộc bài A ở các trạng thái draft/pending_review/published/unpublished đều 400; id ảnh của bài đã xoá (cascade) 400; PATCH với `row_version` lệch + ảnh bài khác → 409 `STALE_VERSION`, không ghi (kiểm `row_version` chạy trước kiểm ảnh); B đủ 20 ảnh riêng + cover ảnh bài A → 400; 21 ảnh của chính B → 400 (giới hạn cũ còn); lớp 1b: chi tiết + danh sách + footer không chứa `image_id`/đường dẫn/alt của ảnh nháp bài A, ảnh của chính bài vẫn hiện.

### Lệch thiết kế / lưu ý
- Không có "xoá mềm" bài trong model (`delete_draft` xoá cứng, cascade ảnh); ca đó được test bằng id ảnh không còn tồn tại.
- Chưa xử lý (ngoài phạm vi, ghi để techlead cân nhắc): `restore_entry_version`/`discard_changes` nạp `cover_image`/`body` từ phiên bản cũ; nếu dữ liệu trước SR-18 trỏ ảnh bài khác thì nháp mang theo. Lớp 1b công khai đã che, và lần lưu body kế tiếp bị 400 BR-ND-07 (cover không đổi thì không kiểm lại). Không sửa vì không có trong AC.
- `publish_entry` không kiểm lại ảnh (bản nháp hợp lệ nhờ lúc lưu); dữ liệu cũ được lớp 1b che.

## Lô 6 — FE

Phạm vi: SR-19 (liên kết bằng chứng đồng ý mở đúng phiên bản chính sách) và SR-20 (màn nghiệp vụ không tải code AI khi AI tắt, BR-AI-17). Chỉ sửa `erp-console/`. Chưa commit.

### Tệp
Mới:
- `erp-console/scripts/check-ai-chunks.mjs`: đọc `.next/app-build-manifest.json`, quét chunk của 2 layout và 4 route nghiệp vụ tìm `new Worker`, `wllama`, `/call/`; mã thoát 1 (đỏ) / 0 (xanh) / 2 (chưa build); in bảng First Load JS.
- `erp-console/features/ai/runtime/messages.ts`: `AI_RUNTIME_MSG.wllamaMissing` (chuyển khỏi `ai/messages.ts` để chunk nghiệp vụ không kéo tên `wllama`).
- `erp-console/features/ai/gate-state.ts`: kho trạng thái nhỏ (`useSyncExternalStore`) `publishAiEnabled`, `useAiEnabledAndConsented`; mặc định tắt (fail-closed).
- `erp-console/features/guidance/components/GuidanceAiActions.tsx`: nút "Để AI làm" và "Nhờ" (tách khỏi `GuidancePanel`).
- `erp-console/features/guidance/components/GuidanceAiSummary.tsx`: nút "Tóm tắt" (tách khỏi `GuidancePanel`).
- `erp-console/features/content/components/PolicyVersionSheet.tsx` + `policy-version.module.css`: panel chỉ đọc "Phiên bản N (khách đã đồng ý)" (dựa trên `SideSheet`: khoá cuộn, bẫy focus, Esc; chỉ dùng token).
- `erp-console/e2e/p8_lo6_fe_sr19_sr20.py`: Playwright (mock), 28 kiểm tra.

Sửa:
- `app/(console)/content/edit/page.tsx`: đọc `version` (chỉ chấp nhận `^\d{1,9}$`, > 0), mở `PolicyVersionSheet` sau khi bài đã tải; "Về bài" và Esc đóng panel.
- `features/guidance/components/GuidancePanel.tsx`: không import tĩnh code AI, không gọi `ai/status`; đọc `useAiEnabledAndConsented()`; nạp `GuidanceAiActions` và `GuidanceAiSummary` bằng `next/dynamic({ ssr: false })`, chỉ render khi AI bật và đã đồng ý. Thông báo kết quả đi qua portal vào thẻ `.aiHost` (`display: contents`) nên bố cục cũ không đổi.
- `features/guidance/components/guidance.module.css`: thêm `.aiHost`.
- `features/ai/api.ts`: `getAiStatus` công bố `ai_enabled` vào `gate-state` (lỗi thì công bố tắt).
- `features/ai/consent.ts`: thêm `subscribeAiConsent` để giao diện phản ứng khi Chủ đổi đồng ý.
- `features/ai/messages.ts`, `features/ai/runtime/wllama.ts`: chuyển `wllamaMissing` sang `runtime/messages.ts`.
- `features/content/mock.ts`: chính sách bảo mật 2 phiên bản (v1 "MẪU-V1..." đăng 01/08/2026, v2 "MẪU-V2..." đăng 20/09/2026), phiên bản không có thì 404. Slug `chinh-sach-quyen-rieng-tu` (tránh trùng ca test CMS-12).
- `features/auth/mock.ts`: bổ sung 8 quyền `content.*` cho `chu` và `quan_ly`, khớp migration BE `content/0002_grant_content_perms` (mock cũ thiếu nên mock không vào được màn Nội dung). `nv_kho` không có, đúng thực tế.
- `features/guidance/mock.ts`: bước `create_refund` của đơn không phải giữ chỗ có `ai: { level: "C" }` để e2e SR-20-AC5 có nút "Để AI làm" (chỉ mock).

### TDD SR-20 (đỏ, rồi xanh)
Đỏ, chạy `node scripts/check-ai-chunks.mjs` sau `npm run build` khi chưa tách (mã thoát 1):
```
ĐỎ: code AI còn nằm trong chunk màn nghiệp vụ (BR-AI-17):
  - layout console: chunk static/chunks/app/(console)/layout-616e52e18c01dee9.js chứa "wllama"
  - /orders, /orders/payments, /orders/refunds, /inventory: chunk static/chunks/6877-5834223bd119dfea.js chứa "new Worker", "wllama", "/call/"
  - (4 route trên): chunk static/chunks/1013-db843afd0baddeaa.js chứa "wllama"
```
Xanh sau khi tách (mã thoát 0): `XANH: 4 màn nghiệp vụ và 2 layout không chứa new Worker, wllama, /call/.`

### First Load JS trước và sau
Số liệu của script (tổng chunk JS chưa nén):
| Route | Trước | Sau |
|---|---|---|
| layout gốc | 309,7 kB | 309,7 kB |
| layout console | 373,0 kB | 373,5 kB |
| /orders | 443,5 kB | 430,6 kB |
| /orders/payments | 456,5 kB | 443,7 kB |
| /orders/refunds | 419,2 kB | 406,3 kB |
| /inventory | 398,2 kB | 385,3 kB |

Số liệu của `next build` (đã nén):
| Route | Trước | Sau |
|---|---|---|
| /orders | 138 kB | 133 kB |
| /orders/payments | 141 kB | 136 kB |
| /orders/refunds | 130 kB | 125 kB |
| /inventory | 124 kB | 119 kB |
| Shared | 88,2 kB | 88,2 kB |

### Kết quả kiểm
- `npx tsc --noEmit`: sạch. `npm run build` (mock=0 và mock=1): sạch. `npm test`: 103/103. `node scripts/check-ai-chunks.mjs`: mã thoát 0.
- Build thật `NEXT_PUBLIC_USE_MOCK=0`: `grep -rlE "demo1234|0900000|Khách Giả|mockGet" out/` = 0 tệp.
- Không màu hex trong tệp mới (chỉ token). Không lưu dữ liệu cá nhân vào localStorage/URL/console (URL chỉ có `id` và `version`).

### Playwright (mock, cổng 3216, 28/28 PASS)
Chạy: `BASE=http://127.0.0.1:3216 SHOTS=doc/features/2026-09-30-sua-loi-review/qa-lo6 python3 erp-console/e2e/p8_lo6_fe_sr19_sr20.py`.
- SR-19-AC1: Chủ mở đơn có đồng ý, bấm "Xem phiên bản" → panel "Phiên bản 1 (khách đã đồng ý)", nội dung MẪU-V1, không lẫn MẪU-V2, "Đăng lúc 10:00 01/08/2026 (giờ Việt Nam)", không có ô nhập, href chỉ `id` + `version`.
- SR-19-AC2: `version=99` → "Không tìm thấy phiên bản 99" + nút "Về bài" (360 px không cuộn ngang); `version=2` hiện bản 2.
- SR-19-AC3: `ql1` thấy liên kết; `kho1` không có mục Đơn hàng và không thấy liên kết.
- SR-20-AC3: AI tắt, mở `/orders` + chi tiết đơn, `/orders/payments`, `/orders/refunds`, `/inventory` → 0 request `/api/ai/*`, không có nút "Để AI làm".
- SR-20-AC5: AI bật + đã đồng ý, mở tab Trợ lý (có `GET /api/ai/status/`), bấm "Để AI làm" → `POST /api/ai/commands/sales.refund.create/call/` và thông báo "AI đã soạn nháp đề xuất". AI bật nhưng chưa đồng ý → không có nút.
- Không có `console.error`.
Ảnh trong `doc/features/2026-09-30-sua-loi-review/qa-lo6/`: `sr19-ac1-desktop.png`, `sr19-ac2-mobile360.png`, `sr19-v2-mobile360.png`, `sr20-ac3-orders-detail-desktop.png`, `sr20-ac3-payments-desktop.png`, `sr20-ac3-refunds-desktop.png`, `sr20-ac3-inventory-desktop.png`, `sr20-ac5-before-desktop.png`, `sr20-ac5-after-desktop.png`, `sr20-orders-detail-mobile360.png`. Ảnh dùng dữ liệu mock bịa; font icon offline nên biểu tượng hiện thành chữ cái (không ảnh hưởng nội dung).

### Lệch thiết kế / lưu ý
1. Trước đây không có context "AI bật" nào để màn nghiệp vụ đọc. Tạo `gate-state.ts` và sửa `ai/api.ts`, `ai/consent.ts` (ngoài danh sách tệp của 02c). `AiAssistantGate` không đụng, vẫn gọi `getAiStatus` như cũ.
2. Hệ quả: nút "Để AI làm" và "Tóm tắt" chỉ hiện sau khi tab Trợ lý đã mở ít nhất một lần trong phiên (lúc đó status mới được công bố). Chưa mở thì coi như AI tắt (an toàn, không gọi `ai/status` từ màn nghiệp vụ).
3. Nút "Nhờ" (DW-23) nay cũng nằm trong khối nạp động, nên bị ẩn khi AI tắt (trước đây hiện luôn). Nếu PO muốn "Nhờ" hiện cả khi AI tắt thì cần tách riêng (đường gọi `escalateStep` phải ra khỏi `ai/actions/api`).
4. Sửa `features/auth/mock.ts` và `features/guidance/mock.ts` (ngoài danh sách 02c) chỉ để mock chạy được e2e; không ảnh hưởng bản build thật.
5. Tiêu đề panel khi không tìm thấy là "Phiên bản N" (không kèm "khách đã đồng ý" vì không có bằng chứng).
6. Hàm `dateTime` dùng chung không đặt `timeZone`; panel phiên bản tự dùng `Asia/Ho_Chi_Minh` và ghi "(giờ Việt Nam)". Các màn khác chưa đổi.

### Nợ còn lại
- `/ai-spike` vẫn chứa code AI (SR-23 F12, ngoài Lô 6).
- Cần rà tay kích thước thật trên thiết bị yếu (TTI < 2 s) khi QA đo; mới đo dung lượng chunk, chưa đo thời gian.

## Lô 6 — FE Shop (M5-1b, B2)
Phạm vi: chỉ `frontend/`. Không đụng `erp-console/`, package.json/lock, backend, `02*.md`. Không commit.

### B1 (Medium) — bản build thật không còn seed mock
Nguyên nhân: `lib/api.ts`, `features/content/api.ts`, `features/site/api.ts` import tĩnh `./mock` (dù nhánh gọi đã có điều kiện literal), và `CheckoutScreen.tsx` gọi `dynamic(() => import("./MockGatewayPanel"))` ở cấp module (chunk kéo theo `lib/mock`). Bundler giữ module vì import tĩnh có thể có hiệu ứng phụ.
Đã sửa:
- `frontend/lib/api.ts`, `frontend/features/content/api.ts`, `frontend/features/site/api.ts`: bỏ import tĩnh `./mock`; mỗi nhánh mock là `if (process.env.NEXT_PUBLIC_USE_MOCK === "1") { const m = await import("./mock"); return m.mockXxx(...) }`. Hành vi bản mock không đổi (các hàm vốn async).
- `frontend/features/checkout/components/CheckoutScreen.tsx`: `MockGatewayPanel = process.env.NEXT_PUBLIC_USE_MOCK === "1" ? dynamic(...) : null`; render khi `MockGatewayPanel && ?mock_gateway=1`.
- Script mới `frontend/scripts/check-no-mock.mjs [thư-mục-build=out]`: đọc `mock*.ts` và `Mock*.tsx` để lấy seed (khoá `cangcaloc_*`, `DH-DEMO*`, `item_code` mẫu, SĐT `0900000*`, mật khẩu demo nếu có, tên mẫu có khoảng trắng, nhãn cổng giả lập), quét mọi js/html/txt/json/css/map trong `out/`; exit 1 nếu thấy. 27 chuỗi seed hiện tại.

Đỏ trước khi sửa (build thật `NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=https://example.invalid`):
```
check-no-mock: 4 file mock, 27 chuỗi seed, 46 file build (out/)
  LỌT MOCK  out/_next/static/chunks/116-af53a0319b0dba58.js  "cangcaloc_mock_orders_v2", "DH-DEMO001..004", "CA-BASA-PHILE", "TOM-SU-TUOI", "MUC-ONG", "NGHEU-TRANG", "Mực ống"
  LỌT MOCK  out/_next/static/chunks/351.63e1c941295ab008.js  "Giả lập — chỉ hiện ở chế độ mock"
check-no-mock: ĐỎ — 11 chỗ lọt seed mock vào bản build.     exit=1
grep -rlE "DH-DEMO00|CA-BASA-PHILE|cangcaloc_mock_orders" out/  ->  out/_next/static/chunks/116-af53a0319b0dba58.js
```
Xanh sau khi sửa (43 file build, ít hơn 3 chunk):
```
check-no-mock: XANH — không thấy seed mock nào trong bản build.   exit=0
grep -rlE "DH-DEMO00|CA-BASA-PHILE|cangcaloc_mock_orders" out/  ->  (rỗng, grep exit 1)
```
Lưu ý: script tự bắt được `MockGatewayPanel` lọt chunk riêng (351) mà lệnh grep của QA không thấy; đó là lý do sửa cả `dynamic(...)`.
Bản mock (`NEXT_PUBLIC_USE_MOCK=1`) đương nhiên đỏ với script này (bản mock có seed) — script chỉ dùng cho bản thật.

### B2 (Low)
`frontend/features/checkout/storage.ts` `recallOrderContact`: chỉ trả về khi `phone_last4` là chuỗi khớp `/^\d{4}$/`, ngược lại `null` (không vào ô nhập, không vào URL).

### Kiểm chứng
- `npx tsc --noEmit`: exit 0.
- Build thật xanh + `check-no-mock.mjs` exit 0 + grep rỗng (trên).
- `e2e/qa-lo6-sr21-shop.py` chạy trên build thật (cổng 3106, out copy sang scratchpad): 279 ca, 0 FAIL, 0 LOW (M5-1 nay PASS, ca B2 nay không còn cảnh báo).
- Build mock `NEXT_PUBLIC_USE_MOCK=1`, Playwright nhanh (390px): `/shop/` hiện "Cá basa phi lê"; `/shop/orders/` tra `DH-DEMO001` + `6789` ra đơn; `/shop/checkout/?mock_gateway=1&...` hiện màn cổng giả lập; không pageerror.
- Cuối cùng `frontend/out/` được build lại là BẢN THẬT với `NEXT_PUBLIC_API_BASE=https://cangca-api-675411800433.asia-southeast1.run.app` (production, theo `doc/ops/moi-truong.md`), check-no-mock xanh.

### Đề xuất / nợ
- `erp-console/scripts/check-no-mock.mjs` chưa làm (fe-dev khác đang sửa `erp-console/`); script frontend viết theo cấu trúc chung nên copy sang được (đổi nguồn seed nếu ERP có mật khẩu demo ở `features/auth/mock.ts`). Đề xuất gắn vào quy trình build/deploy: chạy `node scripts/check-no-mock.mjs` sau `npm run build` bản thật, trước `firebase deploy`.

### Lô 6 — FE: sửa thêm (điều phối kiểm `check-no-mock`)
Điều phối chép `frontend/scripts/check-no-mock.mjs` sang `erp-console/scripts/check-no-mock.mjs`. Build thật rồi chạy thì ĐỎ (9 chỗ):
- Nguồn lọt thật, chỉ một: `erp-console/features/content/api.ts`. Có 2 lỗi.
  - `const isMock = ...` gán ra biến rồi dùng `mock: isMock ? ... : undefined`. Bundler không cắt được nhánh mock nên `features/content/mock.ts` cùng seed đi vào chunk `108-*.js`. Các api.ts khác đã viết `process.env.NEXT_PUBLIC_USE_MOCK === "1"` nguyên văn tại chỗ dùng nên không lọt.
  - `fetchShopCatalog` có `mock: () => ({ ... "CA-THU-1KG", "MUC-ONG-1KG", "Mực ống Phan Thiết 1kg" ... })` không có điều kiện, nên 4 mã hàng mẫu nằm luôn trong bản thật.
- Cách sửa: bỏ biến `isMock`, viết điều kiện literal nguyên văn tại từng chỗ dùng (kèm chú thích); bọc mock của `fetchShopCatalog` trong `process.env.NEXT_PUBLIC_USE_MOCK === "1" ? ... : undefined`. Không cần `await import("./mock")` vì literal nguyên văn đã đủ để bundler cắt (các api.ts khác đang xanh nhờ đúng cách này); không đổi hành vi bản mock (mock 1 build lại, e2e Lô 6 vẫn 28/28).
- 2 chỗ còn lại trong 9 là báo nhầm: `staff/page` và `ai-spike/page` chứa chuỗi "deactivate", bị regex mật khẩu bắt do đứng sau dấu phẩy trong `["edit", "set_groups", "reset_password", "deactivate"]`. `/ai-spike` không phải nguồn lọt (Lô 7 xoá nó).
- Sửa heuristic mật khẩu ở CẢ `erp-console/scripts/check-no-mock.mjs` và `frontend/scripts/check-no-mock.mjs` (2 tệp giống hệt nhau):
  - Chỉ lấy chuỗi gán cho khoá tên đúng `password`/`PASSWORD`/`mat_khau`/`mật khẩu` với `:` hoặc `=`, có lookbehind để "reset_password" không tính; bỏ dấu phẩy khỏi mẫu.
  - Thêm luật: mọi chuỗi dạng `"demo\d{3,}..."` trong tệp mock đều là seed, không phụ thuộc tên khoá. Kiểm lại: chạy trên bản build mock thì `demo1234` (từ `features/auth/mock.ts`) được báo, tức script không bỏ sót; chạy trên bản thật thì không có.
- `frontend/scripts/check-no-mock.mjs` chạy trên `frontend/out/` đang có (không build lại vì QA đang dùng thư mục đó): XANH, exit 0. Nếu điều phối cần bằng chứng trên bản build mới của frontend thì cần build lại ở phiên khác.

Kiểm cuối (build thật `NEXT_PUBLIC_USE_MOCK=0`, `erp-console/out/` hiện là bản thật):
- `node scripts/check-no-mock.mjs` (erp-console): XANH, exit 0 (12 tệp mock, 31 chuỗi seed, 134 tệp build).
- `node scripts/check-ai-chunks.mjs`: XANH, exit 0.
- `npx tsc --noEmit`: sạch. `npm test`: 103/103.
- `grep -rlE "demo1234|0900000|Khách Giả|mockGet" out/`: 0 tệp.
- Bản mock: build lại + `e2e/p8_lo6_fe_sr19_sr20.py` 28/28 PASS.

### F6-1 — nút "Nhờ" không phụ thuộc AI (techlead review Lô 6, mức High)
**Lỗi:** sau SR-20, nút "Nhờ" (DW-23) nằm trong `GuidanceAiActions`, mà khối đó chỉ nạp khi AI bật và đã đồng ý. Kết quả: AI tắt thì mất luôn "Nhờ". Sai với DW-23-AC7 ("AI tắt → Nhờ vẫn chạy"); BE cũng không chặn escalate khi AI tắt.

**Sửa (chỉ `erp-console/`):**
- `features/guidance/components/GuidanceEscalate.tsx` (mới): nút "Nhờ" + thông báo kết quả (portal vào `noticeHost`). Điều kiện hiện giữ nguyên như cũ: `!step.allowed && step.actor !== "system" && step.key`. Không đọc cờ AI bật/đồng ý.
- `features/guidance/components/GuidancePanel.tsx`: `StepItem` render `GuidanceEscalate` tĩnh (import thường, không `next/dynamic`), đứng trước `{aiOn && <GuidanceAiActions/>}`. Điều kiện hiện nút "Để AI làm" KHÔNG đổi (F6-2 / D6-1 chờ Duy quyết).
- `features/guidance/components/GuidanceAiActions.tsx`: bỏ toàn bộ code "Nhờ"/escalate, chỉ còn "Để AI làm".
- `features/ai/actions/api.ts` (viết lại, thuần http): `escalateStep` nằm ở đây và được import tĩnh. Để bản build thật không lọt seed, phần mock đã tách sang `features/ai/actions/mock.ts` (mới: `mockAiActions` 4 dòng, `mockUndoAiAction`, `mockFetchAiActions`, `mockFetchAiActionDetail`, `mockConfirmAiAction`, `mockRejectAiAction`, `mockEscalateStep`). Mỗi lời gọi viết `mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? () => mockX(...) : undefined` nguyên văn, nên bundler cắt được. Trước đây `mockAiActions` là seed cấp module ngay trong `api.ts`; import tĩnh `api.ts` vào màn nghiệp vụ sẽ kéo seed vào bản thật (chứa uuid `a1b2c3d4-...`).
- `features/ai/actions/actions.test.ts`: chỉ đổi dòng import (`mockAiActions`, `mockUndoAiAction` lấy từ `./mock`); 103/103 vẫn xanh.

**Lệch cần biết:**
1. **SR-20 AC3 "0 request /api/ai/*"** mâu thuẫn nhẹ với DW-23: "Nhờ" gọi `POST /api/ai/actions/escalate/` (đường dẫn nằm dưới `/api/ai/` nhưng không phải tính năng AI). Cách hiểu tôi áp dụng: AC3 nghĩa là khi MỞ màn (không ai bấm gì) có 0 request `/api/ai/*`, và không bao giờ có `/api/ai/commands` hoặc `/api/ai/status` khi AI tắt. Request escalate do NGƯỜI BẤM "Nhờ" là ngoại lệ hợp lệ. E2E kiểm đúng như vậy (xem dưới). Nếu PO muốn AC3 chặt hơn, cần sửa câu chữ AC3 hoặc đổi đường dẫn escalate (việc BE, ngoài phạm vi FE).
2. **`features/guidance/mock.ts` (ngoài danh sách file 02c):** mock cũ chỉ có bước `allowed:false` ở nhánh lô kho (`close`). Đơn, thanh toán, hoàn tiền đều `allowed:true` nên không có màn nào hiện "Nhờ" để test. Thêm hàm `chuOnlyStep` và 3 bước người dùng `allowed:false` (chỉ Chủ): `cancel_paid` (nhánh đơn đã thanh toán), `confirm_manual` (thanh toán), `cancel_refund` (hoàn tiền). Chỉ ảnh hưởng mock; không test đơn vị nào phụ thuộc số bước (đã grep).
3. **Sửa e2e cũ:** kiểm lại phát hiện ca SR20-AC3 cho payments/refunds/inventory dùng bộ chọn liên kết quá lỏng (`Thanh toán`, `Hoàn tiền`, `Kho|Tồn kho`), ảnh chụp cũ cho thấy có thể đứng ở danh sách đơn thay vì đúng màn. Đã đổi sang tên liên kết chính xác ("Hàng chờ thanh toán", "Phiếu hoàn chờ chuyển", "Kho & lô") và thêm `expect` hàng danh sách của đúng màn; kết quả vẫn 0 request `/api/ai/*` khi mở màn. Ảnh `sr20-ac3-payments/refunds/inventory-desktop.png` đã chụp lại.

**Kiểm chứng (chạy trong lượt này):**
- `npx tsc --noEmit`: sạch. `npm test`: 103/103.
- Build mock rồi `e2e/p8_lo6_fe_sr19_sr20.py` (cổng 3216, out copy sang scratchpad, đã tắt server): **61/61 PASS** (28 ca cũ + ca F6-1: AI tắt ở 4 màn có "Nhờ", bấm ra thông báo "Đã chuyển việc cho nhóm chu", nút thành "Đã nhờ (chu)" và khoá, 0 request `/api/ai/commands|status`, đúng 1 `POST /api/ai/actions/escalate/`; AI bật đồng ý: có cả "Để AI làm" và "Nhờ", "Để AI làm" chạy như trước; mobile 360 không cuộn ngang).
- Ảnh (`doc/features/2026-09-30-sua-loi-review/qa-lo6/`): `f61-nho-orders-detail-desktop.png`, `f61-nho-payments-desktop.png`, `f61-nho-refunds-desktop.png`, `f61-nho-inventory-desktop.png`, `f61-nho-orders-detail-ai-on-desktop.png`, `f61-nho-orders-detail-mobile360-desktop.png` (tên có hậu tố `-desktop` do hàm chụp gắn cố định; ảnh này là viewport 360).
- Build thật `NEXT_PUBLIC_USE_MOCK=0` (`erp-console/out/` hiện là bản thật): `check-no-mock.mjs` XANH (13 tệp mock, 32 chuỗi seed, 134 tệp build); `check-ai-chunks.mjs` XANH; `grep -rlE "demo1234|0900000|Khách Giả|mockGet" out/` = 0 tệp; `grep -rl "a1b2c3d4-e5f6-7890-abcd-ef1234567890" out/` = 0 tệp; `frontend/scripts/check-no-mock.mjs` trên `frontend/out/` XANH.
- First Load JS (script, chưa nén): /orders 433.3, /orders/payments 446.4, /orders/refunds 409.0, /inventory 388.0, layout console 373.5, layout gốc 309.7 kB. Tăng ~2,7 kB mỗi màn so với trước F6-1 (do `GuidanceEscalate` + `ai/actions/api.ts` đi vào chunk chung), vẫn thấp hơn mốc trước SR-20 (443,5/456,5/419,2/398,2). Next build: /orders 134, /orders/payments 137, /orders/refunds 126, /inventory 120 kB.

### F6-2 (Duy chốt 30/09) — "Để AI làm" theo `step.ai` của server
**Quyết định của Duy:** nút "Để AI làm" hiện khi `step.ai` khác null. Server đã trả `step.ai = null` khi Chủ tắt AI toàn cục, nhân viên tắt AI của mình, lệnh chưa giao/OFF hoặc không có quyền (`backend/apps/common/guidance/steps.py::resolve_step_ai`, `ai/policy/effective.py`). Nút KHÔNG còn phụ thuộc "đã đồng ý tải model" hay việc đã mở tab Trợ lý. Bấm là gọi server như cũ (`POST /api/ai/commands/<lệnh>/call/`). Luồng lớn hơn (Chủ bật → nhân viên opt-in → tab Trợ lý + tải model, router kiểm model) là P9, chưa làm.

**SR-20-AC2 đổi:** trước đây "Để AI làm" hiện khi AI bật VÀ đã đồng ý. Nay "Để AI làm" hiện theo `step.ai` (mức C, có `step.command`). Điều kiện "AI bật + đã đồng ý" (gate-state) chỉ còn áp cho "Tóm tắt" (DW-16, chạy model local). AC3 (AI tắt → 0 code AI, 0 request `/api/ai/commands|status`) vẫn đúng: không bước nào có `step.ai` thì `GuidanceAiActions` không bao giờ được nạp.

**Sửa (chỉ `erp-console/`):**
- `features/guidance/components/GuidancePanel.tsx`: `StepItem` tự tính `showAiButton = step.ai && step.ai.level === "C" && step.command` (giữ đúng DW-14-AC3/AC8 như cũ, chỉ đổi nguồn điều kiện) và chỉ render `GuidanceAiActions` (vẫn `next/dynamic`) khi đúng. Bỏ prop `aiOn` của `StepItem`; `aiOn` (gate-state) chỉ còn dùng cho `GuidanceAiSummary`.
- `features/guidance/components/GuidanceAiActions.tsx`: chỉ đổi chú thích đầu file. `features/ai/commands/call.ts` chỉ import `@/shared/lib/http` và `../types`, không kéo `wllama`/`Worker` (kiểm trên bản build thật: chunk nạp động của `GuidanceAiActions`, 2 kB, có 0 `wllama`, 0 `new Worker`; chunk có `wllama` là chunk cổng Trợ lý, tách riêng và không do màn nghiệp vụ nạp).
- `features/ai/consent.ts`: chỉ sửa chú thích (đồng ý chỉ còn cho Tóm tắt). `gate-state.ts` không đổi.
- Mock (mô phỏng server): `features/ai/mock.ts` export `aiEnabled()`; `features/guidance/mock.ts` bước `create_refund` trả `ai: aiEnabled() ? { level: "C", label: "Để AI làm" } : null` (cờ AI mock tắt → `ai: null`, giống `resolve_step_ai`). Đổi so với trước: mock mặc định tắt AI nên huy hiệu "AI (C)" và nút không còn hiện nếu chưa `__caveMock.ai("on")`. Không test đơn vị nào phụ thuộc.
- Hành vi cần biết: nút nay hiện khi khối nạp động về xong (chunk tải riêng), nên chậm hơn vài chục ms so với các nút khác. Test phải chờ nút (`expect(...).to_be_visible()`), không đếm ngay.

**Kiểm chứng (chạy trong lượt này):**
- `npx tsc --noEmit`: sạch. `npm test`: 103/103.
- Build mock + `e2e/p8_lo6_fe_sr19_sr20.py`: **74/74 PASS**. Ca F6-2:
  - `ai("on")` không cấp đồng ý, tải lại hẳn trang, KHÔNG mở tab Trợ lý: mở chi tiết đơn 102 thấy "Để AI làm" và huy hiệu "AI (C)"; lúc mở 0 request `/api/ai/status|commands`; bấm ra đúng 1 `POST /api/ai/commands/sales.refund.create/call/` + thông báo "AI đã soạn nháp đề xuất", không gọi status; "Nhờ" vẫn cạnh đó.
  - `ai("off")` (`step.ai = null`, kể cả đã đồng ý model, mobile 360): không có nút, không có huy hiệu, 0 request `/api/ai/*`, "Nhờ" vẫn còn, không cuộn ngang.
  - Ca cũ "AI bật nhưng chưa đồng ý: không có nút" đổi thành "vẫn có nút" theo SR-20-AC2 mới.
  - Kịch bản f62 bỏ qua lỗi console "Failed to fetch RSC payload" (do `page.goto` huỷ prefetch đang bay), không phải lỗi app.
- Ảnh (`qa-lo6/`): `f62-de-ai-lam-not-opened-assistant-desktop.png`, `f62-de-ai-lam-after-desktop.png`, `f62-step-ai-null-mobile360.png`.
- Build thật `NEXT_PUBLIC_USE_MOCK=0` (`erp-console/out/` hiện là bản thật): `check-no-mock.mjs` XANH (13 tệp mock, 32 chuỗi seed, 134 tệp build); `check-ai-chunks.mjs` XANH; `grep -rlE "demo1234|0900000|Khách Giả|mockGet" out/` = 0; `grep -rl "a1b2c3d4-e5f6-7890-abcd-ef1234567890" out/` = 0; `frontend/scripts/check-no-mock.mjs` XANH.
- First Load JS (script, chưa nén): /orders 433.3, /orders/payments 446.4, /orders/refunds 409.0, /inventory 388.0 kB (không đổi so với F6-1). Layout console 373.5, layout gốc 309.7.

## Lô 7 — BE

Phạm vi: `backend/` (be-dev). Không đụng `migrations/`, `models/`, `frontend/`, `erp-console/`, `doc/decisions.md`, `02-stories.md`, `02c`. Không commit/deploy. Dữ liệu 100% giả (0900000xxx, "Khách Giả A/B"). Không migration mới (`makemigrations --check --dry-run`: No changes detected).

### Kiểm chứng cuối (chạy trong lượt này)
- `cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test` (không `--parallel`): **Ran 1594 tests ... OK** (nền trước lô: 1523; thêm 71 test mới, 0 failure, 0 error).
- `manage.py makemigrations --check --dry-run`: `No changes detected` (chỉ có cảnh báo cũ `content.W001` về SELLER_*).
- `adapter/` không sửa nên không chạy pytest.

### SR-22
| Mã | Sửa | Test (mới) | Đỏ -> xanh |
|---|---|---|---|
| BM-05 | `apps/ai/actions/services.py`: `confirm_ai_action`/`reject_ai_action` dùng `visible_actions_for(user)` (cùng bộ lọc với `retrieve`). Ngoài phạm vi: 404 `NOT_FOUND`, cùng thông điệp với id không tồn tại, trạng thái không đổi | `apps/ai/actions/tests/test_p8_lo7_bm05.py` (11) | Đỏ khi viết test (việc ngoài phạm vi không trả 404), xanh sau khi cài; số đỏ chi tiết không lưu lại |
| BM-07 | `apps/ai/execution/scrub.py`: `_is_cost_authorized` = `can_view_cost(user)` (quyền `inventory.view_costprice`), không còn tự dò nhóm | `apps/ai/execution/tests/test_p8_lo7_scrub_cost.py` (4). Khoá dò: `purchase_rate`, `landed_unit_cost` (đều thuộc `COST_KEYS`) | Đỏ rồi xanh (số đỏ chi tiết không lưu lại) |
| F07 | `apps/ai/execution/pipeline.py`: mốc đầu ngày của hạn mức ngày dùng `timezone.localtime().replace(hour=0,...)` (giờ VN), không dùng đầu ngày UTC | `apps/ai/execution/tests/test_p8_lo7_daily_limit.py` (2): 08:00 VN có việc lúc 06:30 VN -> được đếm (trước đó bị bỏ sót); 06:30 VN có việc từ 20:00 VN hôm trước -> không đếm (trước đó bị đếm thừa) | Đỏ rồi xanh (số đỏ chi tiết không lưu lại) |
| F08 | `apps/delivery/cskh/services.py::escalate_expired_windows`: khoá `DeliveryNote` (`select_for_update`) **trước** `ConfirmationTask`; thứ tự chung: SalesOrder -> DeliveryNote -> ConfirmationTask | `apps/delivery/tests/test_p8_lo7_lock_order.py` (spy `QuerySet.select_for_update`, kiểm thứ tự model) | Đỏ (thứ tự khoá sai) rồi xanh; số đỏ chi tiết không lưu lại |
| F10 | `apps/ai/actions/services.py::undo_ai_action`: đọc `spec.undo == "cancel_action:<act>"`, dispatch đúng action đó của `spec.view_cls` (không còn mặc định `cancel_receipt`); không có đường hoàn tác (`""`, `defer`, action không có trên view, lệnh mất khỏi registry) -> 400 `AI_CANNOT_UNDO`, trạng thái giữ DONE. Lỗi từ action huỷ giữ mã gốc (ví dụ `BR-MH-07`). Bỏ chặn `AI_ENABLED` 410 ở đường hoàn tác/huỷ lịch (rút lại việc đã có, không phải AI làm thêm) | `apps/ai/actions/tests/test_p8_lo7_undo.py` (8) | 8 đỏ khi viết test, chỉ còn test DW-19-AC10 cũ đỏ sau khi cài (xem "Lệch"); xanh sau khi sửa test cũ |
| F12 | `apps/sales/payments/auto_confirm.py`: (a) xoá nhánh chết `p.sales_order`/CONFIRM_ORDER (02b chốt số 2, chỉ còn ATTACH_TO_ORDER); (b) không có Chủ đang hoạt động -> `logger.warning` và **không** đếm là escalated; (c) `downgrade_reason` và log chỉ ghi **mã lỗi** (`BusinessError.code` hoặc tên lớp lỗi), không ghi `str(exc)` | `apps/sales/payments/tests/test_p8_lo7_auto_confirm.py` (7) | Chứng minh đỏ bằng cách tạm khôi phục bản HEAD của `auto_confirm.py`: 5 đỏ; khôi phục bản mới: xanh |
| NoStore | `SalesOrderViewSet(NoStoreMixin, ...)` (`apps/sales/orders/api.py`) và `CustomerViewSet(NoStoreMixin, ...)` (`apps/sales/customers/api.py`): header `Cache-Control: no-store` | `apps/sales/orders/tests/test_p8_lo7_no_store.py` (4): ma trận chu/quan_ly/nv_kho/nv_giao/cskh + khách 401, danh sách và chi tiết | Đỏ rồi xanh |

### Nợ Tech Lead xử lý (03b)
- **Lô 1 L4** `apps/ai/management/commands/run_due_ai_actions.py`: nhánh AI tắt bọc từng việc bằng try/except (`_downgrade_when_ai_off`); một việc lỗi không làm hỏng các việc sau; log chỉ mã việc, lệnh, tên lớp lỗi. Test `apps/ai/execution/tests/test_p8_lo7_due_ai_off.py`.
- **Lô 2 L5** `apps/sales/refunds/next_steps.py`, `apps/inventory/batches/next_steps.py`, `apps/sales/payments/next_steps.py`: thông điệp 404 cố định, không nhúng `doc_id` ("Không tìm thấy phiếu hoàn tiền." / "Không tìm thấy lô hàng." / "Không tìm thấy giao dịch thanh toán."). Test `apps/common/tests/test_p8_lo7_guidance_404.py`.
- **Lô 2 L2** `apps/ai/registry/tests/test_p8_pii_sweep.py`: fixture có thêm khách B, người nhận (`Người Nhận Giả C`, 0900000789), phiếu giao gán nv_giao, `ConfirmationTask`, phiếu hoàn tiền; lớp `SR24Fixture` khẳng định dữ liệu **không rỗng** và các sentinel không lọt ra API/AI (quét vẫn xanh: rỗng không còn là "xanh giả").
- **Lô 3 L1** `auto_confirm.py`: xoá nhánh chết (trùng mục F12a).
- **Lô 3 L2** `_escalate_to_chu` trả `bool` (True = đã chuyển/cập nhật, False = không có Chủ hoặc no-op); các nơi gọi đếm `escalated`/`skipped` đúng theo giá trị trả về; khi lý do đổi thì cập nhật cả `downgrade_reason` lẫn `args["reason"]`.
- **Lô 6 L6-1** `apps/content/entries/services.py`: ảnh bìa và khối ảnh trong thân bài phải thuộc **chính bài đó**. `restore_entry_version` và `discard_changes` bỏ ảnh bìa lạ (dùng `_own_cover`) và tính lại `content_hash` cho khớp; `publish_entry` chặn 400 `BR-ND-07` với ảnh bìa hoặc khối ảnh thuộc bài khác (`_assert_images_belong_to_entry`). Test `apps/content/entries/tests/test_p8_lo7_cover_scope.py` (9).
- **Lô 5 L5-1 (BE)**: xem contract dưới.

### Contract L5-1: `GET /api/inventory/batches/`
Quyền không đổi: `BusinessModelPermissions` (chu, quan_ly, nv_kho 200; nv_giao, cskh 403; khách 401). Không thêm trường tiền/giá vốn. Tên khoá đúng như fe-dev ERP đang dùng.
- Tham số mới `has_stock`: `1` hoặc `true` -> chỉ lô có `qty_available > 0`. Bỏ trống, `0` hoặc giá trị khác -> không lọc (không lỗi). Kết hợp được với `status` và `item_code`. Đã khai trong `BatchListQuery` (`has_stock` BooleanField) nên registry AI thấy tham số này.
- Khoá mới (đọc, cả danh sách lẫn chi tiết): `item_name` (`item.name`), `supplier_name` (`supplier.name`), `warehouse_name` (`warehouse.name`), `status_label` (`get_status_display`).
- Khoá cũ giữ nguyên.
```
GET /api/inventory/batches/?status=EXPIRED&has_stock=1   (nv_kho)
{"count": 1, "next": null, "previous": null, "results": [
  {"id": 7, "batch_id": "LO-...", "item": 3, "item_code": "TOM-SU-1", "item_name": "Tôm sú loại 1",
   "supplier": 2, "supplier_name": "Đầu mối A", "warehouse": 1, "warehouse_name": "Kho chính",
   "received_date": "2026-09-20", "expiry_date": "2026-09-27",
   "qty_received": "100.000", "qty_available": "3.000", "qty_reserved": "0.000", "qty_sellable": "3.000",
   "status": "EXPIRED", "status_label": "Quá hạn", "closed_at": null}]}
```
Nv_kho không có `purchase_rate`/`landed_unit_cost` (mixin `CostFieldSerializerMixin`); chu/quan_ly có quyền `inventory.view_costprice` thì vẫn thấy như cũ.
- Test: `apps/inventory/batches/tests/test_p8_lo7_list_contract.py` (10): lọc `has_stock`, kết hợp `status`, đúng giá trị 4 khoá, chi tiết cũng có khoá mới, nv_kho không có khoá `COST_KEYS` và không chứa số giá mua giả `180000`, ma trận Group. Đỏ trước khi cài: 3 (1 error thiếu `item_name`, 2 fail: `has_stock` không lọc, chi tiết thiếu khoá); xanh sau: 10/10.
- `apps.inventory apps.ai` sau khi sửa: 434 test OK (registry AI không vỡ).

### SR-24
- **F5(a)** `backend/config/settings.py`: tách `privacy_consent_required(testing, debug, env)`; hằng `PRIVACY_CONSENT_REQUIRED = privacy_consent_required(TESTING, DEBUG, os.environ)`. Chỉ đổi đúng chỗ này trong `settings.py`. Hàm tên chữ thường để không trùng tên hằng cấu hình. Test `apps/sales/orders/tests/test_p8_lo7_privacy_gl03.py::PrivacyConsentFlagFunctionTests` (4): mặc định bật ngoài dev/test, tắt khi test hoặc debug, biến môi trường ghi đè hai chiều (`1/true/yes/on` và `0/false/no/off/rỗng`), hằng đang chạy bằng đúng kết quả của hàm. Test cũ `test_settings_privacy_consent_required_outside_testing_and_debug` (sao chép công thức vào test, không kiểm gì) đổi sang gọi hàm thật. Đỏ: `ImportError: cannot import name 'privacy_consent_required'`; xanh sau khi tách hàm.
- **F5(b)** GL-03-AC10: `test_f5b_gl03_ac10_admin_post_khong_doi_2_field_consent`: `force_login(superuser)`, GET trang sửa `admin:sales_salesorder_change`, dựng dữ liệu form từ chính form Admin (kèm inline), gửi giá trị **khác** cho `privacy_consent_at` và `privacy_policy_version`, POST, `refresh_from_db` -> không đổi. Kèm `test_f5b_admin_khong_hien_2_field_consent_o_dang_sua_duoc` (cả hai nằm trong `readonly_fields`). Ghi chú thật: khi thử bỏ `readonly_fields` khỏi Admin, test POST vẫn xanh vì hai field còn được chặn bởi `editable=False` ở model (lớp bảo vệ thứ hai); test `readonly_fields` thì đỏ. Hai test cùng nhau khoá cả hai lớp.
- **F5(c)** GL-03-AC9: `test_f5c_gl03_ac9_tra_don_co_dong_y_dung_tap_khoa_cong_khai`: đơn CÓ đồng ý (kiểm `privacy_consent_at` khác None), `set(resp.json().keys()) ==` `{order_code, status, status_label, total_amount, lines, delivery, booked_expires_at, cancel_notice}` (đã tính `cancel_notice` do CSKH Lô 3 thêm). Thêm test không chứa tên/SĐT/địa chỉ giả và chữ `privacy`/`consent`/`policy_version` trong thân response.
- **F13** `doc/ops/moi-truong.md`: thêm mục "Biến môi trường và job nền của AI": staging `AI_PRODUCTION_READY=1` và `AI_WRITE_LEVELS_ALLOWED=B`; production giữ `0` và `C`; bảng lịch chạy `run_due_ai_actions`, `auto_confirm_exact_payments`, `process_cskh_deadlines` (kèm `check_cskh_job_health`), khuyến nghị `*/5`, chưa tạo job thật (việc deploy của Duy). Câu V-DW1 ở `02b-tech-design.md` §8 (dòng "Đính chính V-DW1") **đã đúng sẵn** (staging `AI_PRODUCTION_READY=1`, production `0`/`C`, trỏ về `moi-truong.md`) nên không sửa; câu sai vẫn còn ở `doc/features/2026-09-28-ai-digital-worker/02c-giao-viec.md` (dòng V-DW1, ngoài phạm vi được sửa của lô này).

### Lệch so với test/hành vi cũ (cần người review biết)
1. `apps/ai/actions/tests/test_actions_api.py::test_dw11_ac5_permission_denied_on_confirm`: nv_giao confirm việc của người khác trước đây nhận 403; sau BM-05 nhận 404 (không lộ sự tồn tại). Test đổi cho nv_giao là chủ việc để giữ nguyên ý kiểm 403 về quyền lệnh.
2. `apps/ai/execution/tests/test_dw19_level_b.py`: `test_dw19_ac10_undo_ai_disabled_returns_410` đổi tên `test_dw19_ac10_undo_ai_disabled_still_allowed`: hoàn tác/huỷ lịch khi AI tắt không còn 410 `AI_DISABLED` (F10). Id không tồn tại khi AI tắt: 404 `NOT_FOUND`.
3. `test_p8_pii_sweep.py::test_sr05_ac3_nv_giao_de_xuat_partial_update_ngoai_pham_vi...`: fixture mới gán phiếu cho nv_giao nên test bỏ gán trước khi kiểm "ngoài phạm vi".
4. Việc lỗi ở nhánh AI tắt của `run_due_ai_actions` và lỗi ở F12 giữ nguyên trạng thái cũ của việc (không tự đổi thành FAILED); chỉ log mã lỗi. Chưa có quyết định nghiệp vụ cho "việc SCHEDULED lỗi mãi".
5. Undo: mã lỗi của action huỷ được giữ nguyên (`BR-MH-07`...), không gói thành lỗi chung.
6. L6-1: khi khôi phục hoặc bỏ thay đổi, **khối ảnh lạ trong thân bài không bị gỡ** (chỉ ảnh bìa lạ bị bỏ); publish sẽ từ chối bằng 400 `BR-ND-07`. Lý do: không tự sửa nội dung bài của người soạn.

### Nợ còn lại
- N1 (Tech Lead, hẹn P9): `_escalate_to_chu` dùng `get_or_create` theo `(target_model, target_id, command)`; hai Chủ hoặc chạy song song trên Postgres chưa có bằng chứng, SQLite bỏ qua `skip_locked`.
- Chưa có test song song trên Postgres cho khoá `DeliveryNote -> ConfirmationTask` (F08 chỉ kiểm thứ tự khoá bằng spy).
- L5-1 chưa chạy với FE ERP thật (FE đang kiểm bằng mock); URL đã trùng contract trên.
- Câu V-DW1 sai ở `2026-09-28-ai-digital-worker/02c-giao-viec.md` còn nguyên (ngoài phạm vi).

## Lô 7 — FE Shop

Phạm vi: `frontend/` (SR-23 F2, F6, F7, F8, F10; SR-24 F9). Không đụng `erp-console/`, `backend/`, `package.json`.

### File đã sửa / thêm
- `frontend/features/content/safeHref.ts` (viết lại): `isSafeHref`, `isExternalLink`, `isInternalLink`.
- `frontend/scripts/test-safe-href.mjs` (mới): unit test 40 ca (34 `isSafeHref` + 6 `isExternalLink`), không thêm thư viện (dùng `typescript` có sẵn).
- `frontend/lib/api.ts`: nhánh 404/410 của `apiFetch`; bỏ `getSiteInfo` (gộp về `features/site/api.ts`).
- `frontend/lib/types.ts`, `frontend/lib/mock.ts`: bỏ `SiteInfo`, `CskhNoticeConfig`, `mockGetSiteInfo` (trùng với bản trong `features/site`).
- `frontend/features/content/components/ArticleBody.tsx` (thành client component), `ItemCard.tsx` (chỉ hiển thị), `ArticleBody.module.css`, `app/bai-viet/bai-viet.module.css` (thêm `overflow-wrap: anywhere`).
- `frontend/features/site/api.ts` (một `getSiteInfo`, cache Promise 5 phút), `types.ts`, `components/CskhNotice.tsx` + `CskhNotice.module.css` (mới), `components/ConfirmCallNotice.tsx`.
- `frontend/features/checkout/components/CheckoutScreen.tsx`, `PaymentPanel.tsx`.
- `frontend/features/content/mock.ts`: bài mẫu `xss-mau` (không nằm trong danh sách bài; chỉ có ở bản mock).
- Kịch bản e2e mới: `frontend/e2e/qa-lo7-shop-real.py` (build thật, F7/F10/F6), `frontend/e2e/qa-lo7-shop-xss.py` (build mock, F9). `frontend/e2e/qa-lo6-sr21-shop.py`: chỉ đổi bộ chọn của 1 dòng INFO (`.cskh-notice-box` -> `[data-testid=cskh-notice]`).

### F2 — `safeHref` cùng luật bản ERP (+ chặt hơn)
Luật: bỏ khoảng trắng đầu/cuối; rỗng hoặc > 2000 ký tự -> từ chối; khoảng trắng/ký tự điều khiển bên trong -> từ chối; `/...` hợp lệ trừ `//` và `/\`; còn lại chỉ `https:`, `http:`, `mailto:`, `tel:`.
Chạy `node scripts/test-safe-href.mjs`:
- Bản CŨ (`git show HEAD:frontend/features/content/safeHref.ts`): `31/40 đạt, 9 sai` (đỏ) — lọt `//evil.example`, `/\evil.example`, `\\evil.example`, `\evil.example`, khoảng trắng trong URL, ký tự C1, `abc`, chuỗi > 2000, và ném lỗi khi vào là số.
- Bản MỚI: `40/40 đạt, 0 sai`.
- Lệch so với bản ERP (báo fe-dev ERP): `safeHref` ERP (`erp-console/features/content/editor/convert.ts`) đưa href qua `new URL()` nên nhận `abc` và `\\evil.example` (trình duyệt hiểu `\\host` như `//host`). Bản Shop từ chối cả hai và cả ký tự C1. Đề nghị ERP bổ sung cho khớp.

### F6 — chuỗi "Không tìm thấy" và `apiFetch` 404/410
- `grep` toàn `frontend/` (app, features, lib): KHÔNG có trang nào so sánh chuỗi "Không tìm thấy". Các trang dùng `err.status === 404`/`410` và chữ Việt cố định; `getCatalogItem`, `getOrderStatus` bắt 404 -> `null`.
- Lệch thiết kế: `apiFetch` nhánh 404/410 (thêm ở Lô 3, CMS-13) lấy thông điệp từ `body.detail`. DRF trả mặc định `"Not found."` (tiếng Anh) nên có nguy cơ lộ chữ Anh ra người dùng. Đã sửa: `detail === "Not found."` thì dùng lại câu tiếng Việt mặc định. Vì vậy thông điệp lỗi không còn là hằng để so khớp; code gọi phải dựa vào `err.status`, không so chuỗi.
- Chứng cứ Playwright (build thật): 404 `{"detail":"Not found."}`, 410 và 404 tiếng Việt -> trang bài không hiện "Not found", không pageerror.

### F7 — catalog nạp 1 lần cho cả bài
`ArticleBody` gọi `getCatalog()` một lần khi thân bài có `item_card` (bài không có thẻ thì không gọi), dựng `Map<item_code, CatalogItem>` truyền xuống `ItemCard`. Playwright (build thật, chặn API):
- Bài 3 thẻ: đúng 1 request `/api/shop/catalog/`, 0 request `/api/shop/catalog/<mã>/`. Thẻ 1, 2 hiện tên và giá `100.000`; thẻ 3 (`sellable_qty` "0") báo "Tạm hết hàng".
- Bài không có thẻ: 0 request catalog. Catalog 500: vẫn 1 request, bài vẫn đọc được, không pageerror.
- Nợ nhỏ: `ItemCard` đổi `sellable_qty`/`price` (chuỗi từ API) bằng `Number()` (trước so sánh chuỗi). `CatalogGrid` và `app/shop/item` vẫn truyền chuỗi giá vào `formatVnd`; đã kiểm thực tế chỉ hiển thị đúng khi backend trả số, chưa sửa vì ngoài phạm vi Lô 7.

### F8 — `srcset`
API công khai trả 3 cỡ `urls {sm, md, lg}` (webp 480/960/1600, không phóng to; `width` là bề rộng cỡ lớn nhất). `<img>` có `srcSet` (480w, 960w, 1600w; cỡ hẹp hơn ảnh gốc thì hạ bề rộng khai báo và bỏ cỡ trùng) và `sizes="(max-width: 840px) 100vw, 840px"`. Playwright F9 kiểm `srcset` chứa 480w/960w/1600w và `sizes` không rỗng.

### F10 — một khối "Lưu ý xác nhận đơn", một nguồn giờ, một request
- `CskhNotice` dùng chung (form và màn thanh toán). `ConfirmCallNotice` ("sẽ gọi số đuôi ...") dùng `CallNoticeBox`, cùng nguồn giờ.
- Nguồn giờ duy nhất: `callHours(info)` = `cskh_notice.working_hours` khi khối CSKH bật (`CSKH_WORKING_HOURS`); ngược lại `confirm_call_hours` (`SHOP_CONFIRM_CALL_HOURS`); ngược lại mặc định `DEFAULT_CALL_HOURS`.
- `getSiteInfo` chỉ còn một hàm (`features/site/api.ts`), cache Promise 5 phút (xoá cache khi lỗi). Footer, form checkout, màn thanh toán, trang tra đơn dùng chung.
- Playwright (build thật): mở checkout -> `site-info` đúng 1 request; sau khi đặt hàng thành công vẫn <= 1; trang tra đơn 1 request. Cả hai khối cùng hiện `07:00-21:00` (không còn `7:00–20:00`). Khi `cskh_notice=null` thì hộp gọi xác nhận dùng `7:00–20:00` và không có khối CSKH. `site-info` lỗi: form vẫn hiện (theo GL-03-AC5, mặc định bắt buộc đồng ý), không pageerror. SĐT đầy đủ không lộ, chỉ 4 số cuối.
- Cần báo BE/ops (không sửa được ở FE): hai cài đặt `SHOP_CONFIRM_CALL_HOURS` (mặc định "7:00–20:00") và `CSKH_WORKING_HOURS` (mặc định "07:00-21:00") còn lệch nhau; nên gộp một nguồn ở backend.
- Dấu `{/* # CHỜ legal-vn */}` giữ nguyên trong `CskhNotice`.

### F9 — bài mẫu `xss-mau`
`/bai-viet/?slug=xss-mau` (bản mock). Chứa script/img onerror/svg onload dạng chữ, link `javascript:`, `JaVaScRiPt:`, `java\tscript:`, `data:`, `vbscript:`, `//evil.example`, `/\evil.example`, `\evil.example`, `file:`, link hợp lệ (https, http, `/shop/`, mailto, tel), quote, list, ảnh alt/chú thích độc, `item_card` với mã độc. Playwright (mock, 390px và 1280px, mỗi cỡ 26 ca): không dialog, `window.__xss` không đặt, `article script` = 0, không phần tử nào có thuộc tính `on*`, không iframe/svg/img chèn, payload hiện thành chữ, không link `javascript:/data:/vbscript:/file:/`//`/`\``; 10 nhãn link độc chỉ là chữ; link ngoài có `target=_blank` + `rel="nofollow noopener noreferrer"`; nội bộ/mailto/tel không mở tab mới; bấm vào chữ link độc không đổi URL.
- Lỗi thật phát hiện khi làm: tiêu đề bài có chuỗi dài không dấu cách làm trang cuộn ngang ở 390px (`scrollWidth` 407 > 390). Đã thêm `overflow-wrap: anywhere` cho `.title` và `.articleBody`; chạy lại đạt.

### Kiểm chứng (đã chạy trong lượt này)
- `cd frontend && npx tsc --noEmit`: exit 0.
- `node scripts/test-safe-href.mjs`: 40/40.
- Build thật `NEXT_PUBLIC_USE_MOCK=0` + `node scripts/check-no-mock.mjs`: XANH (4 tệp mock, 27 chuỗi seed, 44 tệp build).
- `e2e/qa-lo7-shop-real.py`: 21 ca, 0 FAIL. `e2e/qa-lo7-shop-xss.py`: 52 ca, 0 FAIL. Hồi quy `e2e/qa-lo6-sr21-shop.py`: 279 ca, 0 FAIL, 0 LOW.
- Cổng chất lượng UI: thành phần mới chỉ dùng token (`--color-*`, `--radius`), không hex rời; 390px không cuộn ngang; `ArticleBody.module.css` còn hex cũ có từ trước Lô 7 (nợ, chưa đổi).
- Ảnh (`doc/features/2026-09-30-sua-loi-review/qa-lo7/`): `lo7-f7-bai-3-the-390.png`, `lo7-f9-xss-390.png`, `lo7-f9-xss-1280.png`, `lo7-f10-checkout-form-390.png`, `lo7-f10-thanh-toan-390.png`. Dữ liệu 100% giả. (Ảnh full-page hiện thanh đầu trang dính giữa màn: do chụp cả trang, không phải lỗi giao diện.)
- Nợ: e2e cũ `frontend/e2e/ra_soat_cms06_item_card.py` chạy với backend thật và lọc request `/api/shop/catalog/`; chưa chạy lại vì cần backend.

## Lô 7 — FE ERP

Phạm vi: `erp-console/` (fe-dev). Không đụng `frontend/`, `backend/`, `package.json`/lock, `02*.md`. Không commit/deploy.

### Việc đã làm
- **F12** xoá `erp-console/app/ai-spike/` và `erp-console/spikes/dw02/`. Bản build thật không còn `out/ai-spike`; `check-ai-chunks.mjs` không tham chiếu spike nên không phải sửa. `features/ai/commands/commands.test.ts` đọc `spikes/dw02/index.json` (đã xoá) nên trỏ sang bản y hệt `doc/features/2026-09-28-ai-digital-worker/research/dw01-index.json` (kèm chú thích).
- **F14** `app/print/label/page.tsx`: QR vẽ bằng `<img src="data:image/svg+xml;charset=utf-8,...">` có `alt="Mã QR <barcode>"`, không chèn SVG thô vào DOM. Chuyển về đăng nhập giờ giữ query: `next=/print/label/?note=..&print_no=..` (mã số, không phải dữ liệu cá nhân, đúng bất biến 9). `LoginScreen` chỉ đưa quay lại trang in khi đăng nhập lại đúng người (`cave_erp_last_user`), `safeNext` chỉ nhận đường dẫn nội bộ.
- **Lô 2 L3** `features/purchasing/api.ts`: xoá `DRAFT_STORAGE_KEY`, `getNhapLoDraft`, `saveNhapLoDraft`, `clearNhapLoDraft`. Test DW-17-AC3 ở `purchasing.test.ts` chuyển sang dùng `saveDraft/loadDraft/clearDraft` của `draftStorage` (vẫn kiểm không lưu `rate`, và nháp của người khác không đọc được).
- **Lô 2 L4** `AuthProvider` không import `purchasing/draftStorage` nữa. `shared/lib/drafts.ts` có `NHAP_LO_DRAFT_PREFIX = "cave_draft_nhap_lo"`; `clearAllDrafts()` xoá tiền tố này ở cả localStorage (khoá cũ) lẫn sessionStorage (nháp SR-07). `draftStorage.ts` import hằng từ shared.
- **Lô 3 L4** `features/cskh/CskhCallModal.tsx`: đổi người nhận, huỷ xác nhận, quyết định Quản lý dùng chung `reportActionError` (`isStaleStateError` -> khối `cskh-stale-alert` + nút "Tải lại", như thao tác gọi); nút gửi của 3 biểu mẫu khoá khi đang stale.
- **Lô 4 L1** timeline đơn: thêm `credit_note_issued` vào `TimelineKind` (`features/orders/types.ts`) và icon `description` trong `OrderDetailView`. Nhãn "Lập chứng từ đảo doanh thu DC-<mã hoá đơn> (x đ)" do BE trả (`orders/timeline.py`); FE chỉ hiện. Mock `orders/mock.ts` sinh mốc này cho đơn CANCELLED có hoá đơn.
- **Lô 5 L5-1 (FE)** danh sách lô: `getBatchesByStatus("EXPIRED")` gọi `GET /api/inventory/batches/?status=EXPIRED&has_stock=1`, bỏ lọc phía client; dùng `item_name`, `supplier_name`, `warehouse_name`, `status_label` (đủ cột NCC và Kho luôn hiện ở chế độ lọc). Cập nhật `types.ts`, `mock.ts` (mock lọc `has_stock=1`), README.
- **SR-23 F2 (ERP)** `features/content/editor/safeHref.ts` (mới) chép nguyên luật của Shop (`isSafeHref`, `isExternalLink`), không import chéo sang `frontend/`. `convert.ts`, `TiptapEditor.tsx`, `PolicyVersionSheet.tsx` dùng `isSafeHref`; hàm `safeHref` cũ (phân giải bằng `new URL`) đã bỏ. Vitest `safeHref.test.ts` chạy cùng 40 payload với `frontend/scripts/test-safe-href.mjs` (34 ca `isSafeHref` + 6 ca `isExternalLink`). Đỏ trước: với bản cũ chép vào `safeHref.ts` cho 4 ca sai (`\\evil.example`, `\evil.example`, C1 0x85, `abc`) = 36/40; xanh sau: 40/40. Test cũ về `safeHref` trong `convert.test.ts` chuyển sang file mới.
- Sửa kèm: `shared/ui/globals.css` khối thẻ hoá bảng trên mobile: luật `tr:last-child td` (độ ưu tiên cao hơn `td.m-*`) làm dòng cuối bị sai bố cục (tên mặt hàng lọt xuống dòng đầu, lệch với các dòng trên). Chỉ còn `border:0` cho dòng cuối. Áp cho mọi bảng `table.data` ở ERP; xem ảnh `l5-1-mobile-375-lo-qua-han.png`.

### Mock mới (chỉ có khi `NEXT_PUBLIC_USE_MOCK=1`, không lọt build thật)
- `window.__caveMock.cskhArmStale(noteId)`: lần thao tác kế tiếp (đổi người nhận / huỷ xác nhận / quyết định) trả 409 `STALE_STATE` và đưa phiếu sang huỷ + báo hoàn tiền.
- `window.__caveMock.cskhSetStatus(noteId, status)`: đổi trạng thái phiếu (ví dụ `PREPARING` để hiện nút "Huỷ xác nhận đơn").

### Kiểm chứng (đã chạy trong lượt này)
- `cd erp-console && npx tsc --noEmit`: exit 0. `npm test`: 11 file, 140 test đạt.
- Build thật `rm -rf .next out && NEXT_PUBLIC_USE_MOCK=0 npm run build`: xong. `node scripts/check-no-mock.mjs`: XANH (13 tệp mock, 32 chuỗi seed, 131 tệp build). `node scripts/check-ai-chunks.mjs`: XANH (layout gốc 308,3 kB; layout console 372,2 kB; /orders 432,0 kB; /orders/payments 445,1 kB; /orders/refunds 407,7 kB; /inventory 386,7 kB). `ls out/ai-spike`: không tồn tại. Bản build thật chứa `has_stock=1`, không chứa `demo1234`, `0900000`, `Khách Giả`, `__caveMock`.
- Playwright (mock, cổng 3217, `out` sao chép sang thư mục riêng): `erp-console/e2e/p8_lo7_fe_erp.py` 79/79 (desktop 1280 và mobile 375): F14 (chuyển đăng nhập giữ query, quay lại đúng tem, `<img data:image/svg+xml>` vẽ được, không `<svg>` thô, vẫn gọi in), CSKH stale cho 3 thao tác (đúng `detail` của BE, nút Tải lại >= 44px, nút gửi khoá, cảnh báo nằm trong khung nhìn, Tải lại đóng hộp thoại), timeline credit note (đúng định dạng VNĐ, đúng thứ tự sau "Huỷ đơn"), danh sách EXPIRED (3 lô, cột NCC/Kho, nhãn "Quá hạn"), `/ai-spike/` 404, console không có SĐT/tên khách.
- Hồi quy sau khi sửa CSS (chạy lại trên bản mock mới): `p8_lo5_fe_lo_qua_han.py` 77/77 (0 FAIL; có 15 dòng console "Failed to fetch RSC payload" do `http.server` tĩnh không phục vụ RSC, thoát bằng điều hướng cứng, không ảnh hưởng), `sr07_nhap_lo_draft.py` 18/18, `sr09_ac4_stale_state.py` 22/22, `p8_lo6_fe_sr19_sr20.py` 74/74.
- Ảnh (`doc/features/2026-09-30-sua-loi-review/qa-lo7/`): `f14-*`, `l1-*-timeline-credit-note.png`, `l4-*-{doi-nguoi-nhan,huy-xac-nhan,quyet-dinh}-stale.png`, `l5-1-*-lo-qua-han.png` (mỗi loại có bản `desktop-1280` và `mobile-375`). Dữ liệu 100% giả. Icon Material Symbols hiện thành chữ trong ảnh vì máy chụp không tải được phông (môi trường, không phải lỗi).

### Lệch / nợ
- Tem in là khổ vật lý cố định 100x150mm (~378px) nên ở màn 375px rộng hơn ~3px: chủ đích cũ, không đổi (e2e cho phép ở mobile).
- Mock không đi qua mạng nên URL `status=EXPIRED&has_stock=1` chỉ kiểm bằng kết quả hiển thị và bằng `grep has_stock=1 out/` ở bản build thật; chưa chạy với backend thật.
- Quyết định Quản lý ở màn CSKH: mock không phân quyền theo vai (e2e đăng nhập `cs1`); BE thật kiểm quyền riêng.
- Còn nợ cũ, ngoài phạm vi: nhiều style hex nội tuyến trong `CskhCallModal.tsx` và `CskhQueueView.tsx`.
- Chưa có hồi quy bằng trình duyệt cho trình soạn bài Tiptap (`isSafeHref` chỉ được unit test và tsc/build); href không có giao thức (ví dụ `abc`) giờ bị từ chối ở ô nhập link.

### L7-1 — open redirect ở đăng nhập ERP (techlead review Lô 7, Medium)
- **Lỗi:** `safeNext` (`erp-console/shared/lib/nav.ts`) chỉ chặn `//`, nên `/login/?next=/%5Cevil.example` (giải mã thành `/\evil.example`, trình duyệt hiểu là `//evil.example`) và `/%09/evil.example` lọt qua; `LoginScreen.destination` đẩy người đã đăng nhập sang trang ngoài.
- **Sửa:** `safeNext` chỉ nhận chuỗi bắt đầu đúng bằng `/` (không trim), ký tự thứ hai không phải `/` hay `\`, không có ký tự mã <= 32 hoặc 127-159, không quá 2000 ký tự; ngược lại trả `null` (về trang mặc định theo `homePath`). Đây là luật nhánh "đường dẫn nội bộ" của `features/content/editor/safeHref.ts`, chép vào `nav.ts` (không import từ `features/content` vào `shared/lib`, theo luật module). Các nơi tạo `next` (`ConsoleGate`, `AuthProvider`, `app/print/label/page.tsx`) vẫn `encodeURIComponent`, không đổi.
- **Vitest** `shared/lib/safeNext.test.ts` (18 ca). Đỏ trước khi sửa: 7 ca sai (`/\evil.example`, `/%5C…` sau giải mã, tab, xuống dòng, C1, quá 2000 ký tự); xanh sau: 18/18. Từ chối: `//evil.example`, `/\evil.example`, `/\t/evil.example`, `\t//evil.example`, `https://evil.example`, `javascript:alert(1)`, `\evil.example`, rỗng, `null`. Giữ nguyên: `/orders/?id=1`, `/print/label/?note=1&print_no=1`, `/`, `/inventory/?status=EXPIRED`.
- **Playwright (mock, cổng 3217)** `erp-console/e2e/l7_1_open_redirect.py` 16/16: đã đăng nhập rồi mở `/login/?next=` với `/%5Cevil.example`, `/%09/evil.example`, `//evil.example`, `https://evil.example`, `javascript:alert(1)` -> luôn ở lại `127.0.0.1:3217` (`/overview/`), không có điều hướng tới host khác; `next=/print/label/?note=32&print_no=1` hợp lệ vẫn được theo. Hồi quy: `p8_lo7_fe_erp.py` 79/79, `sr09_ac4_stale_state.py` 22/22, `sr07_nhap_lo_draft.py` 18/18.
- **L7-5 (comment):** `frontend/features/content/safeHref.ts` đầu file: bỏ câu "chặt hơn ERP" (không còn đúng vì ERP đã chép nguyên luật). Đây là thay đổi duy nhất trong `frontend/` (chỉ comment; `node scripts/test-safe-href.mjs` vẫn 40/40, `tsc` sạch).
- **Kiểm chứng:** `erp-console`: `tsc --noEmit` exit 0; `npm test` 12 file, 158 test đạt; build thật `NEXT_PUBLIC_USE_MOCK=0` + `check-no-mock` XANH (13 tệp mock, 32 chuỗi seed, 130 tệp build) + `check-ai-chunks` XANH (layout gốc 308,3 kB; console 372,3 kB; /orders 432,1 kB; /orders/payments 445,2 kB; /orders/refunds 407,8 kB; /inventory 386,9 kB); `out/ai-spike` không tồn tại; `out/` hiện là bản thật.

## Lô 8 — FE Shop
SR-25 phần Shop (`frontend/`): tiền VNĐ và ngày giờ giờ Việt Nam. Lời Duy 30/09: "đơn vị tiền tệ là VNĐ, GMT +7 … hiển thị phải là +7". Gồm RA-01 (API trả `price` dạng chuỗi Decimal `"260000.00"`, `formatVnd` cũ hiện `260000.00đ`).

**File đã sửa (chỉ `frontend/`):**
- `lib/format.ts` viết lại. `formatVnd(string|number|null|undefined)` ép `Number`, làm tròn, `vi-VN` -> `"260.000 ₫"` (cùng kiểu `erp-console/shared/lib/format.ts::vnd`), rác/rỗng/null -> `"—"`. `formatKg` nhận cả chuỗi. Hàm ngày giờ mới, mọi hàm ép `timeZone: "Asia/Ho_Chi_Minh"` (một `Intl.DateTimeFormat` duy nhất + `formatToParts`, `hourCycle: h23` nên không ra "24:30"): `formatDateTime` ("01/10 00:30"), `formatDate` ("01/10/2026"), `formatTime` ("00:30"), `formatDateOnly` (ngày thuần "2026-10-28" -> "28/10/2026", không đổi múi giờ), `todayVn()` ("YYYY-MM-DD" giờ VN, AC4), `currentYearVn()`.
- Thay chỗ tự định dạng: `app/bai-viet/page.tsx`, `app/trang/page.tsx`, `features/content/components/LatestPosts.tsx` (3 bản `formatDate` chép tay dùng `toLocaleDateString` không `timeZone` -> dùng hàm chung); `app/shop/orders/OrderLookup.tsx` (ngày hoàn `toLocaleDateString` -> `formatDate`; hạn hoàn in thô "2026-10-28" -> `formatDateOnly`; bỏ `Number()` thừa quanh `refund.amount`); `components/CatalogGrid.tsx` (tồn kho `toLocaleString` -> `formatKg`); `features/content/components/ItemCard.tsx` (bỏ `Number()` thừa); `app/page.tsx` (năm bản quyền `getFullYear()` -> `currentYearVn()`); `lib/mock.ts::genOrderCode` (ngày mã đơn theo `todayVn()`).
- Kiểu (`lib/types.ts`): `CatalogItem.price` và `sellable_qty` từ `number` -> `string | number` (API thật trả chuỗi Decimal, trước đây khai `number` là khai sai). Nơi tính toán ép rõ: `components/AddToCartControl.tsx` (`Number(item.price)` khi bỏ vào giỏ; `Number(sellable_qty) > 0`), `CatalogGrid.tsx`/`app/shop/item/page.tsx` (`Number(item.sellable_qty) > 0`). `CartLine.price` giữ `number`.
- `components/CartContext.tsx`: nạp giỏ từ `localStorage` ép `price` về số (giỏ cũ của khách đã lưu `"260000.00"` dạng chuỗi từ bản trước; không ép thì `qty * price` vẫn ra số nhưng lưu chuỗi và dễ sai về sau). Giỏ vẫn chỉ giữ mã hàng, tên, giá, số lượng (không dữ liệu cá nhân).
- `lib/mock.ts`: catalog mock nay trả `price`/`sellable_qty` dạng CHUỖI giống API thật (`"65000.00"`, `"120.000"`) qua `toWireItem`, seed nội bộ vẫn là số để tính tiền. Mục đích: mock bắt được lỗi RA-01 (trước đây mock trả số nên FE không bao giờ thấy lỗi `260000.00đ`).
- Grep cuối: trong `frontend/` (trừ `e2e/`, `scripts/`) không còn `toLocale*String`/`Intl.*`/`getFullYear`/`getDate` ngoài `lib/format.ts`; không còn `+ "đ"` hay `{…}đ`.

**Không đổi:** `CountdownTimer` (đếm ngược theo mốc backend, không định dạng ngày), `features/site/api.ts` (`Date.now()` chỉ để cache), `lib/mock.ts` các `Date.now()` (mốc TTL, không hiển thị). Không thêm thư viện, không đụng `package.json`/lock, `erp-console/`, backend.

**Quyết định nhỏ:** dấu cách trước `₫` là dấu cách thường (giống ERP), chưa dùng NBSP; nếu Duy muốn tránh xuống dòng giữa số và `₫` thì đổi một ký tự trong `formatVnd` ở cả hai FE.

**TDD đỏ -> xanh.** Test không thêm thư viện: `frontend/scripts/test-format.mjs` (26 ca: tiền, ngày giờ sát ranh giới ngày VN, ngày thuần, `todayVn`, năm), nạp `lib/format.ts` bằng `typescript.transpileModule` như `test-safe-href.mjs`.
- ĐỎ trên `format.ts` cũ (`git show HEAD:frontend/lib/format.ts`, `TZ=America/New_York`): `test-format: 1/26 đạt, 25 sai`. Ví dụ: `formatVnd "chuỗi nguyên": muốn "65.000 ₫", được "65000đ"`; `formatVnd "triệu": muốn "1.250.000 ₫", được "1250000.00đ"`; `formatVnd null: THROW Cannot read properties of null (reading 'toLocaleString')`; `formatDateTime …: THROW mod.formatDateTime is not a function`.
- XANH trên bản mới: `TZ=America/New_York`, `TZ=UTC`, `TZ=Asia/Ho_Chi_Minh`, `TZ=Pacific/Kiritimati` đều `test-format: 26/26 đạt, 0 sai`. Ca chính: `"260000.00"` -> `260.000 ₫`; `"2026-09-30T17:30:00Z"` -> `01/10 00:30`; `2026-12-31T20:00:00Z` -> ngày `01/01/2027`, năm 2027.
- `test-safe-href.mjs` (Lô 7) vẫn `40/40`.

**Playwright** (`frontend/e2e/qa-lo8-shop-format.py`, 54 ca; múi giờ trình duyệt `America/New_York` và `UTC`, đã kiểm `getTimezoneOffset() != -420`):
- Build mock (cổng 3109): `/shop/`, `/shop/item`, giỏ -> checkout (đơn giá, thành tiền, tổng `285.000 ₫`, nút đặt hàng), màn thanh toán, tra đơn `DH-DEMO004` (tiền hoàn `540.000 ₫`, hạn hoàn `28/10/2026`), `/bai-viet`, `/trang`, trang chủ. Tồn kho chuỗi `"120.000"` -> `Còn 120 kg`.
- Build thật + API giả `localhost:8199` chặn bằng `page.route` (cổng 3110), dữ liệu sát ranh giới `published_at = refunded_at = 2026-09-30T17:30:00Z`: giá `"260000.00"` -> `260.000 ₫`, `"1250000.00"` -> `1.250.000 ₫`, tồn `"2.500"` -> `Còn 2,5 kg`; giỏ lưu giá dạng số; giỏ cũ giá chuỗi `x2` -> `520.000 ₫`; màn thanh toán `260.000 ₫`; bài viết/danh sách/trang chủ/trang chính sách hiện `01/10/2026` (giờ VN, không `30/09`); tra đơn "đã hoàn 01/10/2026".
- Bộ quét tiền: mọi token `số + đ/₫` phải khớp `\d{1,3}(\.\d{3})* ₫`, không còn `\d+.\d{2}đ`.
- XANH: `54/54 PASS, 0 FAIL` cả hai múi giờ. ĐỎ trên bản cũ (build từ `git worktree` HEAD, dựng tạm ở scratchpad rồi xoá): `12/54 PASS, 42 FAIL` (ví dụ `[real] /shop/ ... <['260000.00đ', '1250000.00đ', …]>`, `[real] bài viết: 'Đăng ngày: 01/10/2026'` sai vì bản cũ ra `30/09/2026`).
- Hồi quy, build thật, không sửa assert nào: `e2e/qa-lo7-shop-real.py` 21 ca 0 FAIL; `e2e/qa-lo6-sr21-shop.py` 279 ca, 0 FAIL, 0 LOW (assert cũ không khớp chuỗi `đ`; `qa-lo7-shop-real.py` chỉ khớp `"100.000"`, vẫn đúng với `100.000 ₫`).
- Ảnh (390 px, dữ liệu giả): `doc/features/2026-09-30-sua-loi-review/qa-lo8/lo8-{shop,item,checkout,thanh-toan,tra-don}-{New_York,UTC}-390.png` (mock), `lo8-real-{shop,baiviet,tra-don}-{New_York,UTC}-390.png` (build thật). Ảnh `lo8-erp-*` là của FE ERP.

**Kiểm chứng (chạy trong lượt này):** `npx tsc --noEmit` sạch; `npm run build` mock và build thật sạch; `node scripts/check-no-mock.mjs` XANH (4 file mock, 27 chuỗi seed, 46 file build). Bản `out/` cuối cùng là build thật với API base production trong `.env.production` (truyền `NEXT_PUBLIC_*` trực tiếp vì `.env.local` đè), không còn `localhost:8199`.

**Lệch contract / còn nợ:** không lệch contract. Còn nợ: `frontend/` chưa có lệnh `npm test`; `scripts/test-format.mjs` chạy tay (`TZ=… node scripts/test-format.mjs`), chưa nối vào `package.json` vì Duy cấm đụng `package.json` ở lô này.

## Lô 8 — FE ERP
SR-25 phần ERP (`erp-console/`): tiền VNĐ `x.xxx ₫` và mọi ngày giờ theo `Asia/Ho_Chi_Minh` bất kể múi giờ máy. Lời Duy 30/09: "đơn vị tiền tệ là VNĐ, GMT +7 … hiển thị phải là +7". Không đụng `frontend/`, backend, `package.json`/lock, `02*.md`.

**Hàm chung (`erp-console/shared/lib/format.ts`).** `vnd` giữ kiểu `"540.000 ₫"` (chuẩn chung với Shop). Mọi hàm ngày giờ đi qua một `Intl.DateTimeFormat` cố định `timeZone: "Asia/Ho_Chi_Minh"`, `hourCycle: "h23"`, tách bằng `formatToParts` (bản cũ `toLocaleString("vi-VN")` ra chuỗi ngược kiểu `13:30 30-09` và theo giờ máy):
- `dateTime` `"01/10 00:30"`, `dateTimeFull` `"01/10/2026 00:30"`, `date` `"01/10/2026"`, `timeHM` `"00:30"`, `timeHMS` `"00:30:15"` (nhận `string | Date`).
- `todayInVietnam(now?)` `"2026-10-01"` (thay `toISOString().slice(0,10)` là ngày UTC), `dateKeyInVietnam(iso)` (khoá gom ngày), `dateOnly("2026-10-28")` `"28/10/2026"` (ngày thuần của BE như hạn hoàn, HSD, không đổi múi giờ), `vnInputToIso("2026-10-02T09:00")` -> `"…T02:00:00.000Z"` (ô `datetime-local` là GIỜ VN, không phải giờ máy). `VN_TZ` xuất ra để dùng chung.

**Chỗ đã thay bằng hàm chung (AC3, AC4).**
- Ngày giờ: `shared/ui/RightRail.tsx` ("Đã lưu · HH:mm"), `app/(console)/content/edit/page.tsx` (3 chỗ "Đã lưu lúc", lịch sử phiên bản), `features/content/components/PolicyVersionSheet.tsx` (bỏ hàm `vnDateTime` tự chế), `ContentListScreen.tsx` (cột "cập nhật" trước đây in nguyên chuỗi ISO), `app/(console)/ai/actions/page.tsx`, `features/ai/actions/components/ActionDetailModal.tsx` (3 mốc, `timeHMS`), `features/ai/settings/components/MyConfigScreen.tsx`, `features/ai/report/components/AiDailyReportScreen.tsx` + `features/ai/report/api.ts` (ngày báo cáo mặc định = ngày VN), `features/cskh/CskhQueueView.tsx` và `CskhCallModal.tsx` (bỏ 8 chỗ cắt chuỗi `slice(11, 16)` — chỉ đúng khi BE trả `+07:00`; nay đúng cho mọi offset), `features/inventory/components/ActivityFeed.tsx` (gom "Hôm nay/Hôm qua" theo ngày VN, trước theo giờ máy), `features/orders/components/OrdersScreen.tsx` (`vnDate` bộ lọc "Hôm nay/7 ngày/30 ngày"), `features/deliveries/components/DeliveriesView.tsx` (`completed_from` = hôm nay VN), `features/purchasing/components/NhapLoForm.tsx` (ngày nhập lô mặc định = hôm nay VN).
- Nhập giờ: `CskhCallModal.tsx` hẹn gọi lại / gia hạn dùng `vnInputToIso` (trước: `new Date(callbackTime)` hiểu theo giờ máy nên khách hẹn 09:00 ở máy New York thành 13:00 UTC = 20:00 VN). Nhãn ô thêm "(giờ Việt Nam)".
- Tiền: `CskhQueueView.tsx`, `CskhCallModal.tsx` (`Number(x).toLocaleString + " đ"` -> `vnd`), `MyConfigScreen.tsx` (trần lệnh `${cap} đ` -> `vnd`), `CancelOrderForm.tsx` (`Tổng đơn {order.total_amount}` in chuỗi Decimal thô -> `vnd`).
- Ngày thuần in thô `2027-09-20` -> `dd/mm/yyyy` bằng `dateOnly`: `DeliveryDetailModal.tsx` (HSD), `NhapLoForm.tsx` ("Hạn dùng"), `app/print/label/page.tsx` (HSD sớm nhất trên tem), hạn hoàn tiền ở CSKH.
- Mock (để e2e đúng múi giờ, không đổi hợp đồng): `shared/lib/dashboardSummary.mock.ts` và `features/inventory/mock.ts` tính "ngày" theo giờ VN; `features/purchasing/mock.ts`, `features/cskh/mock.ts`; `features/guidance/mock.ts` nhãn tiền `540.000 đ` -> `540.000 ₫` (khớp `backend/apps/sales/utils.py::vnd_display`, nhãn timeline thật của BE).
- Không đổi có chủ đích: `features/orders/mock.ts::vndD` (`300.000đ`) — mô phỏng đúng câu lỗi của BE theo contract S12/S13; các `Date.now()` dùng cho đếm ngược/TTL/cache.

**TDD đỏ -> xanh.** `shared/lib/format.test.ts` (Vitest, 13 ca: tiền `"260000.00"` -> `260.000 ₫`, rác/rỗng/`NaN` -> `—`; ngày giờ qua nửa đêm VN; `todayInVietnam`; `vnInputToIso`) và `shared/lib/noLocalTime.test.ts` (quét mã nguồn: cấm `toLocaleDateString`/`toLocaleTimeString`/`Intl.DateTimeFormat`/`Date#toLocaleString`/`slice(11, 16)`/`toISOString().slice(0, 10)` ngoài `format.ts`, AC3).
- ĐỎ (`TZ=America/New_York npx vitest run shared/lib/format.test.ts`, trước khi sửa `format.ts`): `Tests 8 failed | 3 passed (11)`. Ví dụ: `dateTime qua nửa đêm VN: expected '13:30 30-09' to be '01/10 00:30'`; `timeHM / timeHMS: expected '13:30' to be '00:30'`; `giờ ban ngày: expected '03:05 30-09' to be '30/09 14:05'`; các hàm mới `TypeError: dateTimeFull is not a function`. Quét mã nguồn ĐỎ trước khi thay nốt 2 chỗ mock: `expected [ 'features/cskh/mock.ts:395' ] to deeply equal []`.
- XANH: `TZ=America/New_York`, `TZ=UTC`, `TZ=Asia/Ho_Chi_Minh`: `format.test.ts` 13/13 và `noLocalTime.test.ts` 7/7; `npm test` toàn bộ `Test Files 14 passed, Tests 178 passed` (cả ba múi giờ).

**Playwright** (`erp-console/e2e/p8_lo8_fe_erp_tz.py`, build mock, cổng 3219, `out/` copy sang scratchpad `lo8-erp/`, dữ liệu giả). Đồng hồ trình duyệt cố định `2026-09-30T17:30:00Z` (= `00:30 ngày 01/10` giờ VN, qua nửa đêm) bằng `context.clock.set_fixed_time`; 4 context `America/New_York`, `UTC`, `Pacific/Pago_Pago` và `Asia/Ho_Chi_Minh` (mốc đối chiếu). Đi qua Tổng quan, Đơn hàng (danh sách + chi tiết + timeline), Giao hàng (danh sách + chi tiết), Lô (tồn + tab Hoạt động), Nhập lô (ngày mặc định), CSKH (danh sách + vòng đi-về hẹn gọi lại 09:00).
- Giá trị tuyệt đối theo mốc VN: `Cập nhật 00:30`, `01/10 00:20`, `Đặt 01/10 00:20 · Tới 00:50`, timeline `01/10 00:10`, ngày nhập lô mặc định `2026-10-01`, `Trả tiền: 28/09 06:00`, hẹn `09:00` nhập ra lại `Hẹn gọi lại 09:00`; ở 3 múi giờ máy khác, chuỗi mốc giờ trên từng màn bằng đúng mốc VN, "Hôm nay/Hôm qua" của Hoạt động khớp ngày VN. Bộ quét tiền: 0 token sai kiểu (`\d{4,} ₫` hoặc hậu tố `đ`) ở 8 màn x 4 múi giờ, 60 số tiền `x.xxx ₫` trên Tổng quan/Đơn/Lô; mobile 390 px không cuộn ngang.
- XANH: `71/71 PASS`. ĐỎ trên bản cũ (`git stash -u -- erp-console`, build mock, chạy cùng script, rồi `stash pop`): `42/71 PASS, 29 FAIL` — ví dụ `overview: ['Cập nhật 13:30'] vs ['Cập nhật 00:30']` (New York), `['Cập nhật 17:30']` (UTC), ngày nhập lô `2026-09-30` thay vì `2026-10-01`, hẹn 09:00 ở New York hiện `13:00`, hậu tố `0 đ` trong nhãn timeline.
- Hồi quy trên build mock mới, KHÔNG sửa assert nào (không có assert chuỗi giờ/tiền bị lệch): `e2e/p8_lo7_fe_erp.py` 79/79, `e2e/p8_lo5_fe_lo_qua_han.py` 77/77, `e2e/p8_lo6_fe_sr19_sr20.py` 74/74. Đã tắt server.
- Ảnh (dữ liệu giả, giờ máy New York): `doc/features/2026-09-30-sua-loi-review/qa-lo8/lo8-erp-{1-tong-quan-ny,2-don-chi-tiet-ny,3-lo-ny,4-cskh-ny,5-don-chi-tiet-mobile-ny}.png`.

**Kiểm chứng (chạy trong lượt này):** `erp-console`: `./node_modules/.bin/tsc --noEmit` exit 0; `npm test` 14 file, 178 test đạt; build thật `rm -rf .next out && NEXT_PUBLIC_USE_MOCK=0 npm run build` xong; `node scripts/check-no-mock.mjs` XANH (13 tệp mock, 32 chuỗi seed, 131 tệp build); `node scripts/check-ai-chunks.mjs` XANH (layout gốc 308,3 kB; console 373,4 kB; /orders 433,4 kB; /orders/payments 446,5 kB; /orders/refunds 409,1 kB; /inventory 388,2 kB); `grep -rlE "demo1234|0900000|Khách Giả|mockGet|__caveMock" out/` = 0 tệp. `erp-console/out/` hiện là bản thật.

**Lệch contract / còn nợ (báo Duy/BE, không tự sửa):**
- Câu lỗi BE theo contract S12/S13 viết tiền là `300.000đ` (`backend/apps/sales/utils.py::vnd_display_msg`, `beErrors.mock.ts` "tối thiểu 1đ"), còn nhãn timeline và FE dùng `540.000 ₫`. AC1 "thống nhất một kiểu" cần BE đổi câu lỗi sang `₫` (thuộc backend, ngoài phạm vi lô này); FE hiện in nguyên văn thông điệp BE nên sẽ tự khớp khi BE đổi.
- Thứ tự thu gọn "dd/mm hh:mm" (không năm) ở danh sách vẫn như cũ; chỗ cần năm (lịch sử phiên bản, cột cập nhật bài viết, ngày báo cáo) dùng `dateTimeFull`/`date`.
- Các màn đọc `created_at`/`at` từ BE giả định BE trả ISO có offset hoặc `Z` (Django DRF với `USE_TZ`); nếu BE trả chuỗi không offset thì `new Date()` hiểu theo giờ máy — chưa kiểm với backend thật trong lô này.
- Mock `cskh` vẫn dùng vài màu hex cứng trong `CskhQueueView.tsx`/`CskhCallModal.tsx` (nợ từ trước, không đổi trong lô này).

## Lô 8 — BE

**SR-25 phần BE (AC1 tiền `x.xxx ₫`, AC2 giờ GMT+7, AC5 tên tiếng Anh).** Không đổi model/migration/contract JSON: `refund.amount` trong `cancel_notice` và CSKH vẫn là chuỗi số thô (`"300000"`), ISO trong API giữ nguyên (có offset). Chỉ đổi CHUỖI người đọc do BE dựng.

**Phát hiện lệch giả định đầu vào:** `vnd_display` đã trả `300.000 ₫` (dấu cách thường) từ trước; chuỗi `300.000đ` đến từ `vnd_short` (thông điệp lỗi S12/S13) cùng nhiều literal `{amount}đ`. Không có `vnd_display_msg` như ghi chú FE ERP (tên thật là `vnd_short`).

**File đã sửa**
- Mới `backend/apps/common/formatting.py`: `format_vnd`, `format_local_time`, `format_local_date`, `format_local_datetime` (mọi chuỗi giờ/ngày qua `timezone.localtime`).
- `apps/sales/utils.py`: `vnd_display` gọi `format_vnd`; **xoá `vnd_short`**; `gen_code` lấy ngày mã chứng từ theo giờ VN (`SO-261001-…` khi tạo lúc 00:30 VN, trước đây theo ngày UTC).
- Thông điệp lỗi: `sales/payments/services.py` (`AMOUNT_MIN_MSG` "Số tiền tối thiểu 1 ₫.", BR-TT-09 "Tổng tiền đã nhận 300.000 ₫ < tổng đơn 540.000 ₫."), `sales/refunds/services.py` (`REFUND_AMOUNT_MIN_MSG`, 3 câu "Vượt số … tối đa x ₫").
- `sales/orders/customer_notices.py`: câu báo khách tự huỷ dùng `format_vnd` ("Số tiền 300.000 ₫ sẽ được hoàn…", trước đây `300000đ` không có dấu chấm); ngày hạn/ngày hoàn qua `format_local_date`.
- `sales/payments/auto_confirm.py`: lý do chuyển Chủ "Giao dịch 400.000 ₫ khác tổng đơn 500.000 ₫" (trước đây `400000.00đ`).
- `ai/execution/pipeline.py`: việc chuyển tiền "Chuyển 300.000 ₫ cho phiếu RF-…" (trước đây `300000`).
- `sales/management/commands/backfill_credit_notes.py`: "số tiền bán 300.000 ₫" (trước `:.0f`).
- `__str__` (hiện ở Django admin): `PaymentTransaction`, `Refund`, `PurchaseCost`, `PurchaseCostAllocation`, `PurchaseInvoice`, `ItemPrice` dùng `format_vnd`; `AuditLog.__str__` theo giờ VN (trước đây in giờ UTC).
- Giờ VN: `delivery/cskh/serializers.py` (`refund.deadline` trước đây `strftime` trên UTC → lệch 1 ngày khi phiếu tạo 00:00–07:00 VN), `delivery/cskh/services.py` (câu "đang được … xử lý tới HH:MM" dùng `format_local_time`).

**Đã rà, KHÔNG cần đổi:** timeline (`orders/payments/refunds/batches`) chỉ dùng `vnd_display`, không có giờ trong nhãn; guidance `reasons.py` không có tiền (đã có test quét); `shop_api`/serializers content/catalog/staff đã `localtime(...).isoformat()`; ISO thô (`dashboard_api`, `delivery`, `ai`) giữ nguyên theo giao ước; không có CSV/báo cáo AI dựng chuỗi giờ/tiền (báo cáo AI chỉ trả ISO).

**TDD.** ĐỎ trước khi sửa (chạy 7 file liên quan): `test_p8_lo8_gmt7` `cancel_notice_message_tien_vnd_dau_cham` ("Số tiền 300000đ sẽ được hoàn" thay vì "300.000 ₫"), `cskh_queue_refund_deadline_theo_ngay_vn` (`'2026-10-30' != '2026-10-31'`); `test_dw27_confirm_refund.test_p8_lo8_sr25_ac1_task_summary…` ("Chuyển 300000 cho phiếu" ≠ "Chuyển 300.000 ₫ cho phiếu"); `test_qa_lo4_backfill_leak.test_p8_lo8_sr25_ac1_dry_run…` ("số tiền bán 300000"); `test_dw26_auto_confirm.test_p8_lo8_sr25_ac1_underpaid_reason…` ("Giao dịch 400000.00đ …", đỏ khi tạm stash `auto_confirm.py`); `test_p8_lo8_vnd_gmt7` ImportError `apps.common.formatting` (module chưa có); assert cũ đổi sang `₫` đỏ (7 dòng trong 4 file) ("…1đ." vs "…1 ₫.", "60.000đ." …). Sau sửa: xanh hết.

**Test mới (19):** `apps/common/tests/test_p8_lo8_vnd_gmt7.py` (12: `format_vnd` dấu chấm/không nbsp/half-up, `vnd_display` cùng kết quả, `vnd_short` đã bỏ, `format_local_*` với datetime 17:30Z ra `00:30`/`2026-10-01`, cả khi truyền datetime múi giờ New York, `AuditLog.__str__`, 4 nhóm `__str__` tiền, `gen_code` với 17:30Z → `SO-261001-`); `apps/delivery/tests/test_p8_lo8_gmt7.py` (4: message khách, hạn hoàn ở CSKH và Shop theo ngày VN, câu "tới 00:30" + ISO `2026-09-30T17:30:00+00:00` giữ nguyên); 1 test trong `test_dw27_confirm_refund.py`, 1 trong `test_qa_lo4_backfill_leak.py`, 1 trong `test_dw26_auto_confirm.py`.

**Assert cũ đã đổi (chỉ các assert chuỗi `đ`, 9 dòng, không đổi gì khác):**
- `sales/payments/tests/test_l8_tien_bosung.py`: `MIN_MSG` = "Số tiền tối thiểu 1 ₫."; 2 assert "Số tiền hoàn tối thiểu 1 ₫."; 1 assert "tối đa 60.000 ₫."
- `sales/payments/tests/test_s12_payment_queue.py`: "Tổng tiền đã nhận 300.000 ₫ < tổng đơn 540.000 ₫."
- `sales/refunds/tests/test_s13_refund_payment.py`: "tối đa 100.000 ₫."
- `sales/refunds/tests/test_s15_refund_from_order.py`: "còn được hoàn tối đa 240.000 ₫."
- `sales/payments/tests/test_p8_auto_confirm_idempotent.py`: `assertIn("1000", …)` → `"1.000 ₫"` và `"2000"` → `"2.000 ₫"` (số tiền lý do chuyển Chủ).

**Kiểm chứng (chạy trong lượt này):** `cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test` → `Ran 1667 tests … OK` (1648 cũ + 19 mới, 0 failure); `makemigrations --check --dry-run` → `No changes detected`.

**Còn nợ / báo Duy:**
- Contract chuỗi lỗi S12/S13 đổi `300.000đ` → `300.000 ₫` (và "1đ" → "1 ₫"): FE in nguyên văn nên tự khớp; `erp-console/features/**/beErrors.mock.ts` còn viết `1đ` (thuộc FE, ngoài phạm vi BE).
- `apps/purchasing/receipts/services.py:105` mặc định `received_date = timezone.now().date()` (ngày UTC): tạo lô lúc 00:00–07:00 VN cho ra ngày hôm trước. Là giá trị lưu chứ không phải chuỗi định dạng nên KHÔNG sửa trong lô này; đề xuất đổi thành `timezone.localdate()` (một dòng) khi Duy/Tech Lead duyệt, vì `batch_id` dùng ngày này.
- Chuỗi trong `AuditLog.changes`/`extra` (ISO `isoformat()` UTC) giữ nguyên là dữ liệu máy đọc, không phải câu chữ hiển thị.

### L8-2 (Medium, techlead) và N8-3 — Lô 8 BE

- **L8-2:** `backend/apps/purchasing/receipts/services.py:105` `received_date = timezone.now().date()` → `timezone.localdate()` (ngày nhập mặc định theo giờ VN, BR-MH-01). Không migration, không đụng dữ liệu cũ. `batch_id` (`{item.code}-{received_date:%y%m%d}-…`) và `expiry_date` đều tính từ `received_date` nên tự đúng theo.
- **TDD** `apps/purchasing/receipts/tests/test_p8_lo8_received_date_vn.py` (4 test, cố định `django.utils.timezone.now`). ĐỎ trước khi sửa: `test_l8_2_api_khong_truyen_ngay_sau_nua_dem_vn_lay_ngay_vn` và `test_l8_2_service_khong_truyen_ngay_sau_nua_dem_vn` → `AssertionError: datetime.date(2026, 9, 30) != datetime.date(2026, 10, 1)`. XANH sau sửa: 17:30Z → `received_date == 2026-10-01`, `batch_id` chứa `-261001-`, `expiry_date` = 01/10 + hạn dùng (30 ngày → 2026-10-31; service mặc định 90 ngày); ca 10:00Z vẫn `2026-09-30` / `-260930-`; `received_date` truyền tường minh vẫn được giữ.
- **Lệnh AI `nhap_lo`:** là chính endpoint `POST /api/purchasing/receipts/nhap-lo/` (khai qua decorator `ai_command` ở `receipts/api.py`) gọi cùng `create_and_submit_receipt`, nên được test API bao phủ; không có đường AI riêng khác để test.
- **N8-3:** `format_vnd(None)` → `"—"` (test `test_n8_3_format_vnd_none_ra_gach_ngang`, đỏ trước: `TypeError: conversion from NoneType to Decimal`); `vnd_display(None)` cùng kết quả.
- **Rà `now().date()` trong `backend/apps/**` (không test):** chỉ còn đúng 1 chỗ (đã sửa ở trên). Không có `date.today()`, `utcnow()`, `.date()` trên datetime UTC nào khác. Các chỗ ngày nghiệp vụ còn lại đã dùng `timezone.localdate()` sẵn (`sales/orders/services.py:191`, `catalog/pricing/services.py:12`, `inventory/batches/services.py:45,511`, `inventory/batches/next_steps.py:59`, `reports/dashboard_api.py:52`, `ai/report/api.py:45`); `ai/report/services.py:16-23` dựng mốc đầu/cuối ngày bằng `make_aware(..., get_current_timezone())` = Asia/Ho_Chi_Minh nên đúng.
- **Chỉ liệt kê, KHÔNG sửa (nằm trong test, dùng ngày UTC làm dữ liệu vào tường minh):** `ai/execution/tests/test_dw19_level_b.py` (7 chỗ `timezone.now().date().isoformat()`), `ai/execution/tests/test_call_api.py:58-59`, `ai/actions/tests/test_actions_api.py:42`, `ai/actions/tests/test_p8_lo7_qa_edges.py:145`, `ai/execution/tests/test_p8_lo7_qa_edges.py:78-79`. Có thể lệch 1 ngày nếu test chạy 00:00–07:00 VN, nhưng đây là dữ liệu dựng của test, không phải hành vi sản phẩm; không đổi trong lô này.
- **Kiểm chứng (chạy trong lượt này):** `DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test` → `Ran 1672 tests … OK` (1667 + 4 test L8-2 + 1 test N8-3); `makemigrations --check --dry-run` → `No changes detected`.

### Lô 8 — FE ERP: L8-1 / L8-3 (sau review Tech Lead)
Chỉ sửa trong `erp-console/`; không đụng `frontend/` (phần Shop của L8-3 để P8b).

**L8-1 — tiền trong câu lỗi mock cùng kiểu `₫` như BE.** BE nay trả `300.000 ₫`/`1 ₫` (`vnd_display`).
- `features/orders/mock.ts::vndD` gọi `vnd()` của `shared/lib/format.ts` (bỏ `toLocaleString(...)+"đ"` tự chế); chú thích "tối thiểu 1 ₫" hai chỗ.
- `shared/lib/beErrors.mock.ts`: `TT_AMOUNT_MIN` "Số tiền tối thiểu 1 ₫." và `HT_AMOUNT_MIN` "Số tiền hoàn tối thiểu 1 ₫.".
- `e2e/s12_s13_queue.py` dựng kỳ vọng bằng `" ₫"` (S12-AC4 `paid/total`, S13-AC3 `max`).
- ĐỎ (mock cũ `300.000đ`, script mới, build mock `out_red`): `95/100`, `FAIL S12-AC4 … 'Tổng tiền đã nhận 1.535.000đ < tổng đơn 1.635.000đ.'` (kỳ vọng `… ₫`) và S13-AC3.
- XANH: S12-AC4 đạt; `s14_s16_cancel_refund.py` 43/43.
- Trong lúc chạy lại `s12_s13_queue.py` thấy thêm 2 lỗi CŨ của chính script (không do L8): (a) selector `.queue-error > span` trúng icon `error` (icon là `<span>` đầu) và UI nay nối thêm ` (BR-xx)` sau thông điệp BE → đổi sang `.queue-error > span:last-child` + `startswith(be(...))` (S12-AC5, S13-AC3); (b) 2 ca "vùng bấm chi tiết ≥ 44px" ở 360 px (`Làm mới 88x28`, `Thực hiện 79x25`) vẫn ĐỎ, cả trước lẫn sau khi sửa — nợ UI cũ của màn Hàng chờ thanh toán, không thuộc SR-25. Kết quả cuối `98/100`.

**L8-3 — `shared/lib/noLocalTime.test.ts` chặn thêm đường vòng** (mọi file `app/ features/ shared/` trừ `format.ts` và test; bỏ qua dòng chú thích thuần):
`getHours/getMinutes/getSeconds/getMilliseconds/getDay`, `getDate/getMonth/getFullYear`, `setHours/…/setFullYear`, `toISOString().split|slice|substring|substr`, `toDateString/toTimeString`, mọi `.toLocaleString(`, và tiền hậu tố `đ` (`1đ`, `"đ"`, `${x} đ`). Tổng 14 ca.
- Kiểm thử chính mẫu quy tắc: thả tạm một file có đủ các kiểu trên → 7 ca mới đỏ đúng dòng; xoá file → xanh.
- Chỗ bị bắt trong mã thật: 0 chỗ dùng Date/`toLocaleString`; chỉ bắt 2 chú thích cuối dòng `tối thiểu 1đ` ở `features/orders/mock.ts:768,1167` (đã đổi thành `1 ₫`). `Math.round(n).toLocaleString` chỉ còn trong `format.ts` (`vnd`, `kg`), là chỗ được phép. Không cần ngoại lệ nào.

**Kiểm chứng (chạy trong lượt này):** `tsc --noEmit` exit 0; `TZ=America/New_York npm test` và `TZ=UTC npm test`: 14 file, 185 test đạt; Playwright trên build mock: `s12_s13_queue` 98/100 (2 ca nợ cũ nêu trên), `s14_s16_cancel_refund` 43/43, `p8_lo8_fe_erp_tz` 71/71, `p8_lo7_fe_erp` 79/79, `p8_lo5_fe_lo_qua_han` 77/77, `p8_lo6_fe_sr19_sr20` 74/74. Build thật `NEXT_PUBLIC_USE_MOCK=0`: xong; `check-no-mock` XANH (13 file mock, 32 chuỗi seed, 131 file build); `check-ai-chunks` XANH; `grep` chuỗi mock trong `out/` = 0. `erp-console/out/` là bản thật; server đã tắt.
