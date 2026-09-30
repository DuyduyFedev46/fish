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
