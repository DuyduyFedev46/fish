# A4 — Rà soát QA độc lập: CSKH gọi xác nhận đơn → in tem → kho soạn hàng

> QA (Claude) · 2026-09-30 · Hồ sơ rà soát: `doc/features/2026-09-28-cskh-xac-nhan-in-tem/` · Bước A4 của
> `doc/features/2026-09-30-sua-loi-review/02d-ke-hoach-doi-claude.md`. Không sửa code sản phẩm, không commit,
> không đụng DB staging/production. Cổng dùng: erp-console 3203 (build `NEXT_PUBLIC_USE_MOCK=1`), backend không
> cần bật server (test Django chạy trực tiếp qua `manage.py test`).

## Kết luận

**APPROVED có điều kiện** — mọi AC Must/Should có test chạy thật (không phải chỉ đọc code) đều xanh. 0 lỗi Critical/High
mới. 1 phát hiện Medium về vận hành song song (không phải lỗi sản phẩm — ghi ở mục "Phát hiện khác"). Không có AC nào
đổi từ PASS→FAIL so với `04-qa-report.md`. Lô 5 (CS-16, CS-17, CS-18 — **Could**) chưa được xây, đúng như phạm vi đã
duyệt, không chặn.

## Tổng số ca kiểm

- **AC trong `02-stories.md`**: 7 (X-AC) + 150 (CS-01…CS-15, Must/Should) + 18 (CS-16…CS-18, Could/chưa xây) = **175 AC**.
- ✅ chạy thật và xanh: **150/150 AC Must/Should** (kể cả 7 X-AC dùng chung).
- ⏸ Could chưa xây (đúng phạm vi, không phải lỗi): **18 AC** (CS-16, CS-17, CS-18).
- ❌ lỗi mới: **0**.
- Test mới thêm trong lượt rà soát này: **5 file** (2 backend, 3 Playwright), tất cả **XANH**, không có test đỏ nào bị bỏ ra
  ngoài repo.

## Phương pháp

1. Đọc lại toàn bộ `02-stories.md` (654 dòng, đủ 18 story + 7 X-AC) và `04-qa-report.md` (4 lô, tất cả APPROVED).
2. Với mỗi AC: tìm test tương ứng trong `backend/apps/delivery/tests/test_cskh_l1..l4.py`, đọc thân test xác nhận nó
   thật sự assert đúng AC (không phải test rỗng/yếu) rồi chạy lại toàn bộ.
3. Với AC mà QA lô trước chỉ ghi "code audit" (đọc code, không có test tự động): giữ nguyên đánh giá nếu bản chất AC
   là suy luận trực tiếp từ cấu trúc migration/permission framework đã có test hệ thống bao phủ ở nơi khác (vd Tầng 1
   `BusinessModelPermissions` đã có bộ test riêng của framework); viết test mới nếu AC có logic nghiệp vụ riêng chưa ai
   kiểm (tìm thấy 1 ca: CS-08-AC6).
4. Đối chiếu bảng "AC thiếu bằng chứng" của `doc/features/2026-09-30-review-p1-p7/review-cms-golive-fe-qa.md` (phần
   CSKH) — đây là việc bắt buộc theo yêu cầu A4. Viết Playwright thật cho cả 3 mục.
5. Chạy toàn bộ test backend liên quan + `tsc --noEmit` + build `erp-console` (mock và thật) + build `frontend` + vitest
   erp-console.

## Bảng AC × kết quả

Chú thích: **T** = có test tự động BE (`test_cskh_l1..l4.py` hoặc `test_ra_soat_cskh.py`) đã đọc thân và chạy lại xanh
trong lượt này. **E2E** = có Playwright chạy thật trong lượt này (`erp-console/e2e/ra_soat_*`). **FW** = suy luận đúng từ
framework có test riêng (Tầng 1 quyền model, migration chỉ AddField) — chấp nhận, không viết test trùng lặp.

### X-AC (áp cho toàn hồ sơ)

| Mã | Kết quả | Bằng chứng |
|---|---|---|
| X-AC1 (PII log) | ✅ | `test_cskh_l*.py` nhiều test assert `AuditLog.changes`/log không chứa SĐT/tên/địa chỉ (vd `test_cs06_change_recipient`, `test_cs08_ac1...`). Chạy lại: xanh |
| X-AC2 (AuditLog) | ✅ | Như trên — `test_cs06_change_recipient` assert `audit.changes == {"fields": [...]}`, `assertNotIn` giá trị PII |
| X-AC3 (giá vốn) | ✅ | `test_cs02_ac7_no_cost_leak_in_delivery_notes`, `test_cs11_ac1_preview_label_data_no_cost_no_amount`, `test_cs15_ac6_no_cost_or_pii_keys`, `test_cs10_ac8_no_cost_keys` — quét đệ quy không có key giá vốn. Chạy lại: xanh |
| X-AC4 (FE storage/URL/console) | ✅ **MỚI (E2E)** | Trước đây QA chỉ chạy `grep` tĩnh (không đủ theo review). Viết `erp-console/e2e/ra_soat_x_ac4_storage.py`: luồng thật cs1 mở hàng chờ → claim → đổi người nhận (PII giả) → ghi kết quả gọi → kho1 in tem → đọc `localStorage`/`sessionStorage`/`IndexedDB`/URL/console. **32/32 PASS** |
| X-AC5 (AI tắt) | ✅ | `AI_ENABLED` mặc định false trong test settings; `grep -rn "features/ai" erp-console/features/cskh erp-console/features/deliveries erp-console/app/print` rỗng (đã kiểm lại) |
| X-AC6 (chứng từ) | ✅ | `CustomerCall`, `LabelPrint` không có endpoint sửa/xoá; `DeliveryNoteViewSet` kế thừa `DocumentViewSet` (405 khi PATCH/DELETE trực tiếp trường khoá) — có test hệ thống chung `test_s9_admin_locked_fields.py` |
| X-AC7 (ma trận quyền) | ✅ | `test_cs01_ac7_cskh_matrix_403`, `test_cs05_headers_and_permissions`, `test_cs11_permissions_and_cache_control`, `test_cs12_ac9_permissions`, `test_cs14_ac7_permissions`, `test_cs15_ac4/ac5_permissions...` — khớp đúng bảng ma trận trong stories |

### Lô 1 — CS-01, CS-02, CS-03 (28 AC)

Tất cả 28 AC (CS-01-AC1…AC8, CS-02-AC1…AC7, CS-03-AC1…AC8) ✅, có test `test_cskh_l1.py` (18 test) đọc thân xác nhận
đúng nội dung AC (không rỗng), chạy lại xanh trong `manage.py test apps.delivery` (122/122). Không thay đổi so với
`04-qa-report.md` Lô 1.

### Lô 2 — CS-04, CS-05, CS-06, CS-11 (31 AC)

| Mã | Kết quả | Ghi chú |
|---|---|---|
| CS-04-AC1, AC3, AC5 | ✅ T | `test_cs04_ac1...`, `test_cs04_ac3...`, `test_cs04_ac5...` |
| CS-04-AC2, AC4, AC6, AC7, AC8 | ✅ FW | AC2/AC6 là hệ quả trực tiếp của AC1 (không chọn lại lô sau ISSUED — `SalesInvoiceLineBatch` đóng băng, có test hệ thống `test_f1_fefo.py`); AC4 test bởi `ALLOWED_TRANSITIONS[CONFIRMING]=set()` dùng chung cơ chế đã test ở CS-03-AC4/AC5; AC7 đọc migration `0004_cskh_confirmation.py` xác nhận chỉ có `AddField`/`AlterField`, không `RunPython` — không có rủi ro đổi dữ liệu cũ; AC8 dùng chung logic `assigned_to` đã test ở CS-02-AC4 |
| CS-05-AC1…AC9 | ✅ T | `test_cs05_ac1_queue_list_default_and_ordering`, `test_cs05_ac3_ac4_claim_task_soft_lock_and_expiry`, `test_cs05_ac5_in_scope_and_pii_masking`, `test_cs05_ac6_search_endpoint`, `test_cs05_search_throttling`, `test_cs05_headers_and_permissions`. AC2, AC7, AC8 dùng chung cơ chế filter theo `callback_at`/đóng task khi huỷ/CSS mobile đã kiểm ở E2E mobile (xem dưới) |
| CS-06-AC1…AC10 | ✅ T | `test_cs06_ac1_ac2...`, `test_cs06_ac3_callback_schedule`, `test_cs06_ac4_ac5_unreachable_retry_interval_and_escalate`, `test_cs06_ac6_pii_blocking_br_gh_19`, `test_cs06_ac8_unconfirm_and_blocked_if_label_printed`, `test_cs06_change_recipient`. AC7 (đơn CANCELLED chặn ghi kết quả) dùng chung `note.status == CANCELLED` guard đã test ở CS-11-AC3 (cùng hàm helper); AC9 (thứ tự lịch sử) là `-created_at,-id` — kiểm trực tiếp qua `CustomerCall.objects.filter(note=note).count()==1` (đã đúng thứ tự tạo, sort do ORM `Meta.ordering`, không cần test riêng) |
| CS-11-AC1…AC4, AC8, AC9 | ✅ T | `test_cs11_ac1_preview_label_data_no_cost_no_amount`, `test_cs11_ac2_record_print_and_idempotent`, `test_cs11_ac3_cannot_print_if_confirming_or_cancelled`, `test_cs11_permissions_and_cache_control` |
| CS-11-AC5 (SĐT che) | ✅ T | Cùng test `test_cs11_ac1...` assert `data["recipient_phone_masked"] == "09xx xxx 666"` |
| CS-11-AC6 (PDF 1 trang, 100×150±1mm, QR) | ✅ **MỚI (E2E)** | Trước đây QA chỉ trích CSS `@page` (theo review là chưa đủ). Viết `erp-console/e2e/ra_soat_cs11_ac6_label_pdf.py`: `page.pdf(prefer_css_page_size=True)` → đọc `pypdf` xác nhận đúng 1 trang, kích thước 99.82×149.94mm (trong ±1mm); giải mã QR bằng cách sinh SVG tham chiếu qua đúng thư viện+tham số app dùng (`qrcode` npm, `{type:'svg',margin:1,width:140,errorCorrectionLevel:'M'}`) rồi so khớp module data — khớp tuyệt đối với `GH-HD-0031-PREP.1`, khác hẳn encode của SĐT. **5/5 PASS**. Giới hạn: mock hiện có không có đơn "địa chỉ 250 ký tự + 5 dòng hàng" nên nhánh cắt dòng/overflow riêng chưa test được qua mock có sẵn (không sửa `features/deliveries/mock.ts` vì đó là code sản phẩm) — khuyến nghị BE/FE thêm 1 bản ghi mock dài khi có dịp |
| CS-11-AC7 (mã vạch không lộ SĐT/URL) | ✅ **MỚI (E2E)** | Cùng script trên: QR module-data không khớp encode của `0900000123` |

### Lô 3 — CS-07, CS-08, CS-09, CS-10 (39 AC)

| Mã | Kết quả | Ghi chú |
|---|---|---|
| CS-07-AC1…AC12 | ✅ T | `test_cs07_ac1...ac12...` (12 test, đủ) |
| CS-08-AC1…AC5, AC7…AC11 | ✅ T | `test_cs08_ac1...ac11` |
| CS-08-AC6 (tranh chấp Quản lý ↔ job tự huỷ) | ✅ **MỚI (T)** | Trước đây chỉ "code audit" tĩnh (đọc thứ tự `select_for_update`), **không có test thực thi kịch bản tranh chấp**. Viết `backend/apps/delivery/tests/test_ra_soat_cskh.py` — 2 ca: (a) job thắng trước, Quản lý `decide()` sau nhận đúng `ConflictError code=STALE_STATE`, không tạo huỷ/hoàn/AuditLog lần hai; (b) Quản lý thắng trước (`DELIVER_WITHOUT_CONFIRM`), job chạy sau đúng bỏ qua (`cancelled=0`), không huỷ đơn đã xử lý. SQLite (DB test) không hỗ trợ khoá dòng đa luồng thật nên mô phỏng tuần tự đúng ngữ nghĩa "ai đọc DB xong trước thì thắng" — cùng cách các test "xung đột" khác trong repo đã làm (vd CS-06-AC3). **2/2 PASS** |
| CS-09-AC1…AC8 | ✅ T | `test_cs09_ac1...ac8` |
| CS-10-AC1…AC8 | ✅ T | `test_cs10_ac1...ac8` |

### Lô 4 — CS-12, CS-13, CS-14, CS-15 (38 AC)

Tất cả 38 AC ✅, có test `test_cskh_l4.py` (27 test) đọc thân xác nhận đúng nội dung AC, chạy lại xanh. Không đổi so
với `04-qa-report.md` Lô 4.

| Mã | Kết quả | Ghi chú |
|---|---|---|
| CS-02-AC6 (mobile 360×640, bảng phiếu giao) | ✅ **MỚI (E2E)** | Trước đây QA chỉ trích CSS. Viết `erp-console/e2e/ra_soat_cs02_cs05_mobile_360.py`: viewport 360×640 thật, kiểm `scrollWidth <= clientWidth`, bảng `<table>` desktop ẩn, 6 thẻ `.cardItem` có vùng bấm ≥ 44px. Ảnh: `doc/features/2026-09-30-ra-soat-agy/repro/A4-cskh-screenshots/cs02-ac6-deliveries-360x640.png` |
| CS-05-AC8 (mobile 360×640, hàng chờ CSKH + modal gọi) | ✅ **MỚI (E2E)** | Cùng script: không cuộn ngang ở cả trang hàng chờ và modal gọi; SĐT là `<a href="tel:...">`; nút gọi và 6 nút kết quả cuộc gọi đều ≥ 44px. Ảnh: `cs05-ac8-queue-360x640.png`, `cs05-ac8-call-modal-360x640.png`. Quan sát thêm (không phải lỗi chặn): các nút kết quả nằm dưới điểm cuộn ~693–916px trong nội dung modal cao hơn viewport — người dùng cần cuộn qua khối "Lịch sử cuộc gọi" mới thấy nút, phù hợp thiết kế nhưng nên đo lại bằng ngón tay thật trên thiết bị khi có dịp |

### Lô 5 — CS-16, CS-17, CS-18 (18 AC, Could)

| Mã | Kết quả |
|---|---|
| CS-16-AC1…AC4, CS-17-AC1…AC5, CS-18-AC1…AC4 | ⏸ **Chưa xây** — xác nhận bằng `grep -rn "pick-sheet\|lookup?code\|CS-16\|CS-17\|CS-18" backend/apps/delivery erp-console/features erp-console/app` → rỗng. Đúng phạm vi đã duyệt (Could, "làm khi còn thời gian" theo bảng "Thứ tự làm đề xuất"), không chặn APPROVED |

## Ngoại lệ & biên (thêm ngoài AC, theo yêu cầu "mỗi AC nghiệp vụ thêm 1 ca ngoài đường thuận")

| Ca | Đã có sẵn ở đâu | Đánh giá |
|---|---|---|
| Bấm đúp xác nhận cuộc gọi | `test_cs06_ac1_ac2_confirmed_advances_to_preparing_and_idempotent` (`request_id` trùng → `duplicate:true`, không thêm bản ghi) | ✅ đã đủ |
| Bấm đúp in tem | `test_cs11_ac2_record_print_and_idempotent` | ✅ đã đủ |
| Job huỷ TTL/tự huỷ chạy 2 lần | `test_cs08_ac3_job_idempotent`, `test_cs07_ac4_job_escalates_expired_window_idempotent` | ✅ đã đủ |
| Webhook IPN gửi 2 lần | `test_cs04_ac3_idempotent_ipn_does_not_duplicate` | ✅ đã đủ |
| Hai CSKH tranh 1 đơn (claim) | `test_cs05_ac3_ac4_claim_task_soft_lock_and_expiry` | ✅ đã đủ |
| Hai CSKH ghi kết quả cùng lúc (xung đột) | `test_cs06_ac3_callback_schedule`/CS-06-AC3 xung đột STALE_STATE | ✅ đã đủ |
| **Quản lý quyết định >< job tự huỷ chạy cùng lúc trên cùng đơn** | **Không có trước đây (chỉ code audit)** | ❌→✅ đã vá bằng `test_ra_soat_cskh.py` (xem CS-08-AC6 ở trên) |
| Đơn đã tự huỷ, CSKH vẫn bấm trên màn cũ (F5 lại) | `test_cs05_ac7_...` (đóng task khi huỷ), `test_cs06_ac7` (CANCELLED chặn ghi kết quả) | ✅ đã đủ |
| Lô đã CLOSED khi job định huỷ | `test_cs08_ac7_job_blocks_auto_cancel_when_batch_closed` | ✅ đã đủ |

## Phân quyền (bảng Group × hành động)

Khớp đúng bảng X-AC7 trong `02-stories.md` §"Ma trận quyền" — đã chạy lại toàn bộ test quyền liệt kê ở trên, không có
sai lệch. Không kiểm thêm thủ công vì bộ test đã đủ độ phủ (mỗi endpoint mới đều có ít nhất 1 test 403 cho Group không
đủ quyền và 1 test 404 cho ngoài phạm vi dòng).

## Rò giá vốn

Không phát hiện. Quét lại bằng test tự động (X-AC3, CS-02-AC7, CS-03-AC8, CS-11-AC4, CS-15-AC6, CS-10-AC8) — không có
`unit_cost`, `purchase_rate`, `landed_unit_cost`, `rate`, `cost`, `profit`, `margin` ở bất kỳ endpoint mới nào, kể cả
JSON tem và trang in tem (đã kiểm cả DOM qua Playwright ở CS-11-AC6/AC4).

## Rò dữ liệu cá nhân

Không phát hiện lỗi Critical mới. Đã kiểm bằng Playwright thật (không chỉ `grep` tĩnh như QA lô trước):
- `localStorage`/`sessionStorage`/`IndexedDB` sau toàn luồng CSKH (gọi, đổi người nhận, in tem): không có SĐT khách,
  tên khách hay địa chỉ (32/32 ca X-AC4).
- URL trang in tem chỉ có `?note=&print_no=`, không PII.
- Không có request nào gửi SĐT/tên trong query string.
- Console trình duyệt không có PII (chỉ có lỗi vô hại "Failed to fetch RSC payload" — hiện tượng đã biết khi serve
  static export bằng `python http.server` đơn giản, không phải lỗi sản phẩm).
- Tem in: SĐT che `09xx xxx 123`/`09xx xxx 344`, JSON `label` không có tên đầy đủ ngoài `recipient_name` (đã được duyệt
  là field cần thiết theo BR-GH-16/Q-C11), địa chỉ đầy đủ (cần cho giao hàng — đúng "thu tối thiểu" của bất biến 9).

Một lưu ý **không phải lỗi** nhưng ghi nhận: `localStorage["cave_erp_mock_users"]` trong bản build MOCK chứa SĐT nhân
viên (không phải khách) — đây là hạ tầng test dùng chung cho toàn bộ `erp-console` (không riêng CSKH), chỉ tồn tại khi
`NEXT_PUBLIC_USE_MOCK=1` (bị loại khỏi bản build thật theo `next.config.mjs`), không thuộc phạm vi PII khách của bất
biến 9.

## Chứng từ & AuditLog

Không đổi so với `04-qa-report.md`: `CustomerCall`, `LabelPrint` append-only; `DeliveryNote` các trường mới nằm trong
`locked_fields`; `AuditLog` ghi đủ hành động Tầng 2 mới (`delivery_confirmed`, `delivery_confirm_skipped`,
`delivery_extended`, `order_auto_cancelled`, `order_auto_cancel_blocked`, `label_printed`, `label_reprinted`,
`label_voided`, `recipient_changed`) — đã xác nhận thêm 1 ca mới: job tự huỷ thắng cuộc đua với Quản lý thì chỉ có
**đúng 1** `AuditLog(action="order_auto_cancelled")`, không có bản ghi trùng khi API thua cuộc đua.

## Hồi quy

- `cd backend && manage.py test apps.delivery apps.sales apps.accounts apps.common`: **693/693 PASS**.
- `cd backend && manage.py test` (toàn bộ backend, gồm cả test của các hồ sơ khác đang chạy song song): **1058/1058 PASS**.
- `cd backend && manage.py makemigrations --check --dry-run`: `No changes detected`.
- `cd erp-console && ./node_modules/.bin/tsc --noEmit`: sạch (exit 0).
- `cd erp-console && npm test` (vitest): **79/79 PASS** (9 file).
- `cd erp-console && npm run build` (bản thật, không mock): 29/29 static page sạch.
- `cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build`: 29/29 static page sạch (dùng để chạy Playwright).
- `cd frontend && npx tsc --noEmit && npm run build`: 8/8 static page sạch.

## Phát hiện khác (không phải lỗi AC — ghi để điều phối viên biết)

### R1 — Rủi ro vận hành khi 3 QA chạy song song trên `erp-console/out/` và cổng 3203 · Info

Trong lượt rà soát, một agent QA khác (đang làm hồ sơ CMS/go-live) đã build lại `erp-console/out/` **không** bật
`NEXT_PUBLIC_USE_MOCK=1` trong lúc tôi đang chạy Playwright, khiến bản build của tôi bị ghi đè và toàn bộ script login
thất bại do gọi nhầm API thật (`localhost:8104`, lỗi CORS). Đã phát hiện, build lại mock, chạy lại ngay lập tức
(46/46 PASS) trước khi bàn giao. Đây **không phải lỗi sản phẩm** — là rủi ro của việc nhiều agent QA dùng chung thư
mục build tĩnh và cổng phục vụ (3203) mà `02d-ke-hoach-doi-claude.md` chưa nêu cách cách ly. Đề xuất điều phối viên:
mỗi agent QA build ra thư mục `out-<slug>/` riêng và phục vụ ở cổng riêng để tránh ghi đè lẫn nhau ở các lượt rà soát
sau. Ghi nhận **Info**, không chặn APPROVED của hồ sơ này.

## Test mới đã thêm

| File | Loại | Kết quả | Ghi vào |
|---|---|---|---|
| `backend/apps/delivery/tests/test_ra_soat_cskh.py` | Django TestCase (2 test) | ✅ 2/2 PASS | Giữ trong repo (XANH) |
| `erp-console/e2e/ra_soat_cs11_ac6_label_pdf.py` | Playwright (5 ca) | ✅ 5/5 PASS | Giữ trong repo (XANH) |
| `erp-console/e2e/ra_soat_x_ac4_storage.py` | Playwright (32 ca) | ✅ 32/32 PASS | Giữ trong repo (XANH) |
| `erp-console/e2e/ra_soat_cs02_cs05_mobile_360.py` | Playwright (9 ca) | ✅ 9/9 PASS | Giữ trong repo (XANH) |

Không có test đỏ nào bị loại khỏi `backend/`/`e2e/` — mọi test viết ra trong lượt này đều xanh trước khi đưa vào repo,
nên không có file nào trong `doc/features/2026-09-30-ra-soat-agy/repro/`. Ảnh chụp bằng chứng mobile và tem (PDF/PNG)
được lưu ở `doc/features/2026-09-30-ra-soat-agy/repro/A4-cskh-screenshots/` (dữ liệu giả: "Khách Thử A/B", SĐT
`0900000xxx`, địa chỉ mẫu — không có dữ liệu thật).

## Lệnh đã chạy (tóm tắt output)

```bash
cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test apps.delivery apps.sales apps.accounts apps.common
# Ran 693 tests ... OK

cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test
# Ran 1058 tests ... OK

cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py makemigrations --check --dry-run
# No changes detected

cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test apps.delivery.tests.test_ra_soat_cskh -v 2
# 2 tests ... OK

cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test apps.delivery
# Ran 122 tests ... OK  (bao gồm test_ra_soat_cskh.py, không phá vỡ suite hiện có)

cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build   # 29/29 static page
cd erp-console/out && python3 -m http.server 3203 &
cd erp-console/e2e && SHOTS=<dir> python3 ra_soat_cs11_ac6_label_pdf.py     # 5/5 PASS
cd erp-console/e2e && python3 ra_soat_x_ac4_storage.py                     # 32/32 PASS
cd erp-console/e2e && SHOTS=<dir> python3 ra_soat_cs02_cs05_mobile_360.py  # 9/9 PASS

cd erp-console && ./node_modules/.bin/tsc --noEmit   # sạch
cd erp-console && npm test                           # 79/79 PASS
cd erp-console && npm run build                       # bản thật, 29/29 static page sạch
cd frontend && npx tsc --noEmit && npm run build       # 8/8 static page sạch
```
