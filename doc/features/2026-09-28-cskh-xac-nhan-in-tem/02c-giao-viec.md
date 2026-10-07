# Giao việc — CSKH gọi xác nhận → in tem → kho soạn hàng
> Claude (Tech Lead) · 2026-09-28 · Trạng thái: **SẴN SÀNG CODE (Duy duyệt 28/09 — chạy toàn bộ kế hoạch)**
> Người hiện thực: Gemini CLI / Antigravity theo `AGENTS.md`, lệnh `/lam-tinh-nang 2026-09-28-cskh-xac-nhan-in-tem`.
> Nhánh làm việc: **`main`** (sau khi hồ sơ `2026-09-28-sua-loi-bao-mat` đã merge `wip/autosave` → `main`).

## Điều kiện đầu vào
- `02-stories.md`: ĐÃ DUYỆT (Duy 28/09) · `02b-tech-design.md`: ĐÃ DUYỆT (Duy 28/09 — theo chốt scope).
- **Phải xong trước:** hồ sơ `2026-09-28-sua-loi-bao-mat` trạng thái XONG (Lô 1 + Lô 2 ☑, đã merge `main`). Hồ sơ này dùng
  `apps/common/throttling.py` (`SettingsRateThrottle`) và bản sửa tra đơn Shop (S02) của hồ sơ đó. Kiểm:
  `git log --oneline origin/main | head` có commit merge sửa lỗi bảo mật; `ls backend/apps/common/throttling.py`.
- Trước lô đầu: `git checkout main && git pull --ff-only origin main`; chạy lệnh kiểm chứng BE một lần, ghi **số test gốc** vào
  `03-dev-notes.md`.
- Mọi contract, tên field, mã lỗi, thứ tự khoá: theo `02b-tech-design.md` (§0c ghi chỗ khác bản PO — FE bám 02b).
- Migration: sinh bằng `makemigrations`, đọc file sinh ra; số thứ tự theo `main` lúc làm (hồ sơ khác có thể đã thêm migration).
  **Không** sửa migration đã có.
- Dữ liệu test/mock/ảnh QA **chỉ giả** (`Khách Thử A`, `0900000123`, `Số 1 Đường Thử`). Repo công khai.

## Lô
| ☐/☑ | Lô | Story | BE / FE | Được sửa (thư mục/file) | Không được đụng | Commit |
|---|---|---|---|---|---|---|
| ☑ | 1 | CS-01, CS-02, CS-03 | BE ∥ FE | **BE:** `backend/apps/delivery/models.py`, `delivery/migrations/` (mới), `delivery/api.py`, `delivery/serializers.py`, `delivery/services.py` (`advance_status`, `ALLOWED_TRANSITIONS`), `delivery/admin.py`, `delivery/cskh/__init__.py` + `scope.py` (mới), `delivery/README.md`; `backend/apps/accounts/migrations/` (mới: seed Group `cskh`), `accounts/auth/services.py` (`ROLE_ORDER`, `GROUP_LABELS`, `CAPABILITY_LABELS`, `home_for`); `backend/apps/sales/orders/api.py` (chỉ `get_queryset`); `backend/apps/common/api.py` (chỉ thêm `ConflictError`/`extra` trong `exception_handler`, `NoStoreMixin`); `backend/apps/common/pii.py` (mới); `backend/apps/common/tests/fixtures.py` (chỉ thêm tham số/helper); `backend/config/settings.py` (khối tham số CSKH); test mới; `delivery/tests/test_api.py` (**chỉ** `test_ac_ready_returns_full_note_json` đổi người bấm sang NV kho). **FE:** `erp-console/shared/lib/nav.ts`, `shared/lib/groups.ts`, `erp-console/features/auth/types.ts` (kiểu `home`), `erp-console/features/deliveries/` (mới), `erp-console/app/(console)/deliveries/page.tsx`; `03-dev-notes.md` | `sales/orders/services.py`, `delivery/signals.py`, `sales/models/`, `frontend/`, `adapter/`, `erp-console/features/orders/`, `features/ai/`, migration cũ, `doc/decisions.md`, `02*.md`, test cũ ngoài danh sách | `e874966` |
| ☑ | 2 | CS-04, CS-05, CS-06, CS-11 | BE ∥ FE | **BE:** `backend/apps/delivery/signals.py`, `delivery/services.py` (`create_delivery_note` thêm tham số `status`), `delivery/cskh/services.py`, `api.py`, `serializers.py`, `README.md` (mới), `delivery/labels/` (mới), `delivery/api.py` (action `label`, `label/print`), `backend/apps/sales/orders/services.py` (**chỉ** `_STOCK_STILL_IN_WAREHOUSE` + gọi `close_task_on_cancel`), `backend/apps/accounts/management/commands/seed_demo.py` (nhận `CONFIRMING`, đánh dấu bản ghi mới của phiếu demo), `backend/config/api_urls.py`, `config/settings.py` (tham số Lô 2, `THROTTLE_CSKH_SEARCH`), `apps/common/throttling.py` (**chỉ thêm** lớp `CskhSearchThrottle`); test mới; **sửa test cũ có chủ đích** (danh sách bên dưới). **FE:** `erp-console/features/cskh/` (mới), `erp-console/app/(console)/cskh/page.tsx` (mới), `erp-console/app/print/label/page.tsx` (mới), `erp-console/features/deliveries/`, `erp-console/features/orders/labels.ts` (thêm `CONFIRMING`), `erp-console/shared/lib/nav.ts`, `erp-console/package.json` + `package-lock.json` (**chỉ** thêm `qrcode`, `@types/qrcode`); `03-dev-notes.md` | `issue_invoice`/`payments/services.py`, `sales/refunds/`, `sales/models/`, `frontend/`, `adapter/`, `features/ai/`, migration cũ (Lô 2 **không** có migration mới), `doc/decisions.md`, `02*.md` | `6c550af` |
| ☑ | 3 | CS-07, CS-08, CS-09, CS-10 | BE ∥ FE (+ Shop) | **BE:** `delivery/cskh/services.py`, `api.py`, `serializers.py` (action `decide`, job, `REFUND_CALL`), `delivery/management/commands/process_cskh_deadlines.py`, `check_cskh_job_health.py` (mới), `backend/apps/sales/models/refunds.py` (**chỉ** `created_by` null) + `sales/migrations/` (mới), `sales/orders/services.py` (lý do `UNREACHABLE`, `SYSTEM_CANCEL_REASON_CODES`), `sales/orders/customer_notices.py` (mới), `sales/orders/shop_api.py` (**chỉ** `ShopOrderLookupView`: `cancel_notice`, `status_label`), `backend/apps/common/site_info_api.py` (mới, hoặc thêm khoá vào view GL-01 nếu đã có), `config/api_urls.py`, `config/settings.py`; test mới; test S02-AC3 của hồ sơ sửa lỗi bảo mật (**chỉ** tập khoá 7 → 8). **FE ERP:** `features/cskh/` (khối Quyết định, lọc Báo huỷ & hoàn), `features/orders/types.ts` (`created_by: number \| null`), `features/orders/components/OrdersScreen.tsx` (**chỉ** mở chi tiết + RefundForm từ `?order=&open=refund`), `features/orders/mock.ts`. **FE Shop:** `frontend/lib/api.ts`, `lib/types.ts`, `lib/mock.ts`, `frontend/app/shop/orders/OrderLookup.tsx`, `frontend/features/checkout/components/` (câu báo trước); `03-dev-notes.md` | `sales/refunds/services.py` (dùng, không sửa), `payments/`, `adapter/`, `features/ai/`, `frontend/features/checkout/gateway.ts`, `storage.ts`, migration cũ, `doc/decisions.md`, `02*.md` | `fd515a5` |
| ☑ | 4 | CS-12, CS-13, CS-14, CS-15 | BE ∥ FE | **BE:** `delivery/cskh/services.py`, `api.py`, `serializers.py` (`recipient`, `WANT_*`), `delivery/labels/services.py`, `delivery/api.py` (action `label/void`), `sales/orders/services.py` (**chỉ** thêm `update_delivery_address`), `backend/apps/reports/attention_api.py` (mới), `config/api_urls.py`, `config/settings.py`; test mới. **FE:** `features/cskh/` (form đổi người nhận, nhãn "Khách muốn huỷ/đổi"), `features/deliveries/` (In lại, Đã huỷ tem, cảnh báo tem cũ), `app/print/label/page.tsx` (dấu IN LẠI), `erp-console/features/overview/components/AttentionBlock.tsx` (mới) + `OverviewScreen.tsx` (**chỉ** gắn khối), `features/overview/api.ts`, `mock.ts`, `types.ts`; `03-dev-notes.md` | `Customer` / `default_address`, `SalesOrder.phone`, `sales/models/`, `payments/`, `refunds/`, `frontend/`, `adapter/`, `features/ai/`, migration cũ, `doc/decisions.md`, `02*.md` | `879efcd` |
| ☑ | 5 | CS-16, CS-17, CS-18 | BE ∥ FE | **BE:** `delivery/models.py` (`CallScript`), `delivery/migrations/` + `accounts/migrations/` (mới: quyền `callscript`), `delivery/cskh/` (API kịch bản, `scripts` trong chi tiết), `delivery/api.py` (action `lookup`), `delivery/labels/services.py`, `accounts/auth/services.py` (**chỉ** nhãn quyền mới nếu có), `config/api_urls.py`; test mới. **FE:** `erp-console/app/print/pick-sheet/page.tsx` (mới), `features/deliveries/` (quét/gõ mã tem), `features/cskh/` (hiện kịch bản; màn soạn kịch bản cho Chủ); `03-dev-notes.md` | như Lô 4; không thêm thư viện quét mã (dùng `BarcodeDetector` khi có, máy quét USB là bàn phím, luôn có ô gõ tay) | BE feefad7 · FE 541e207 |

### Test cũ được sửa có chủ đích (chỉ các chỗ này — ghi từng dòng vào `03-dev-notes.md` kèm lý do BR)
- **Lô 1:** `backend/apps/delivery/tests/test_api.py::test_ac_ready_returns_full_note_json` — người bấm PREPARING→READY đổi từ
  `nv_giao` sang user `nv_kho` (CS-03-AC6: NV giao không soạn hàng, cần `delivery.pack_deliverynote`). Các test khác của file
  giữ nguyên (404 phạm vi phải đứng **trước** 403 quyền: gọi `get_object()` rồi mới `require_perm`).
- **Lô 2** (BR-GH-11 — phiếu mới vào `CONFIRMING`):
  - `backend/apps/common/tests/fixtures.py::make_order_with_note` thêm `confirmed=True` (mặc định) → sau signal đưa phiếu về
    `PREPARING` + task `DONE` (mô phỏng đã xác nhận). Thêm helper `confirm_note_for_test(note)` và `make_confirming_note(...)`.
    Nhờ vậy test dùng fixture **không phải sửa**.
  - Test đi qua luồng thanh toán thật: chỉ được (a) đổi kỳ vọng `PREPARING` → `CONFIRMING`, hoặc (b) chèn
    `confirm_note_for_test(note)` trước bước soạn/giao. Phạm vi: `apps/sales/orders/tests/test_s14_cancel_paid_order.py`,
    `test_s10_api.py`, `test_l7_bosung.py`, `test_f1_fefo.py`, `apps/sales/payments/tests/test_s11_confirm_manual.py`,
    `test_s12_payment_queue.py`, `test_p3_sepay_gateway_ipn.py`, `apps/accounts/demo/tests/test_d1_seed_demo.py`.
  - Không xoá test, không nới assert, không tắt kiểm quyền. Test cũ khác đỏ → **Lệch thiết kế**, dừng lô.
- **Lô 3:** test S02-AC3 của hồ sơ sửa lỗi bảo mật (tập khoá tra đơn) thêm `cancel_notice` (7 → 8 khoá).

---

## [x] Lô 1 — Nền: Group `cskh`, phạm vi dữ liệu cá nhân, bảng + chi tiết phiếu giao (QA APPROVED 2026-09-29)
**Việc (theo `02b` §2, §3, §4.2):**
- Migration `delivery/0004_cskh_confirmation` (toàn bộ schema §2.1–§2.4, gồm `ConfirmationTask`, `CustomerCall`, `LabelPrint`)
  + data migration Group `cskh` và 5 quyền Tầng 2 mới cho `chu`/`quan_ly`/`nv_kho`/`cskh` theo bảng §3.1.
- `scope.py` + áp vào `SalesOrderViewSet.get_queryset` (dùng `Exists`). `me`: `home="cskh-queue"`, nhãn "CSKH", nhãn 5 quyền.
- `DeliveryNoteViewSet`: `StandardPagination`, lọc `completed_from`, thứ tự nhóm, field mới (`order`, `paid_at`,
  `confirmed_at`, `lines_summary`, `total_kg`, `label`, `customer_name`, `address`, `available_actions`), chi tiết có `lines`
  (từ `SalesInvoiceLineBatch`, có `expiry_date`, **không** `unit_cost`). `set_status`: `from_status`/`already`,
  `BR-GH-11`/`BR-GH-07`/`STALE_STATE`, `pack_deliverynote` khi `to_status=READY` (sau `get_object()`), `required_perms=()`.
- Admin: `exclude` hai field người nhận; `locked_fields` thêm field không-PII.
- FE: `GROUP.cskh`, `GROUP_LABEL`, `home` mới, `homePath`; `features/deliveries` (bảng nhóm theo trạng thái — thẻ trên
  điện thoại, chi tiết phiếu, nút "Đã đóng gói" gửi `from_status`, nhãn "Chưa in tem"); mock đủ 7 trạng thái; không nút cho
  `CONFIRMING`.

**Lệnh kiểm chứng** (dán output tóm tắt vào `03-dev-notes.md`):
```bash
cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run
cd backend && .venv/bin/python manage.py test apps.delivery apps.accounts apps.sales apps.common
cd backend && DATABASE_URL=sqlite:////tmp/cskh_l1.sqlite3 .venv/bin/python manage.py migrate && DATABASE_URL=sqlite:////tmp/cskh_l1.sqlite3 .venv/bin/python manage.py migrate   # DB tạm, lần 2 "No migrations to apply"
cd erp-console && npx tsc --noEmit && npm run build
cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build
```
**Test bắt buộc:**
- CS-01-AC1 (migrate 2 lần, đúng tập quyền từng Group; `reverse` gỡ sạch), AC2, AC3…AC7 (scope đơn `cskh`: D1/D2/D4 có, D3 không;
  8 ngày → 404, `CSKH_PII_RECENT_DAYS=10` → 200; người khác gọi → 404; `/api/sales/customers/{id}/` → **403**), AC8.
- CS-02-AC1…AC5, AC7; CS-03-AC1…AC8 (AC3 không có AuditLog thứ hai; AC6 `giao1` 403; AC7 `cs1` 403).
- Không rò giá vốn: token **mọi** Group trên list/detail phiếu giao, list/detail đơn — duyệt đệ quy khoá giá vốn.
- `test_s47_moi_quyen_meta_permissions_deu_co_nhan` và toàn bộ suite cũ xanh.

**Điều kiện xong:** lệnh trên sạch · QA APPROVED mục Lô 1 (`04-qa-report.md`, gồm X-AC3, X-AC7 cho endpoint của lô, CS-02-AC6
mobile 360×640 trên mock) · commit `Lô 1 CSKH: CS-01 nhóm cskh + phạm vi PII, CS-02 bảng phiếu giao, CS-03 soạn hàng` →
`git push origin main`.

---

## [x] Lô 2 — Luồng xác nhận chạy được sớm nhất (gọi → xác nhận → in tem tay → soạn) (QA APPROVED 2026-09-29)
**Việc (`02b` §1.3–§1.6, §4.3, §6):**
- Signal → `start_confirmation(invoice)`: phiếu `CONFIRMING` + `ConfirmationTask(PENDING)` trong một transaction; IPN lặp không
  sinh mục thứ hai. `cancel_paid_order`: `CONFIRMING` hoàn kho; gọi `close_task_on_cancel` (import trong hàm).
- `delivery/cskh`: list/detail/claim/search/calls/unconfirm theo §4.3, máy trạng thái §1.4 đủ mọi mã (trừ `NOTIFIED`), thứ tự
  khoá §1.5, `request_id`, BR-GH-19 kiểm ghi chú, AuditLog chỉ mã, `Cache-Control: no-store`, `required_perms` §8.
- `delivery/labels`: `GET label` (xem trước + `?print_no`), `POST label/print` (idempotent), BR-GH-09/07/16.
- `seed_demo --remove`: nhận `CONFIRMING` như `PREPARING`, gỡ cả `ConfirmationTask`/`CustomerCall`/`LabelPrint` của phiếu demo.
- FE: menu "Gọi xác nhận"; hàng chờ (mặc định + lọc), chi tiết (claim khi mở, `tel:`, nút kết quả ≥ 44 px ở nửa dưới, lịch sử
  gọi, "Đang được … xử lý tới hh:mm"), tìm bằng **POST body**, huỷ xác nhận; nút "In tem" ở chi tiết phiếu giao → trang
  `/print/label/?note=&print_no=` (§6). **Không** `useDraft`/storage/URL cho dữ liệu cá nhân, không `console.*`.

**Lệnh kiểm chứng:**
```bash
cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run
cd backend && .venv/bin/python manage.py test apps.delivery apps.sales apps.accounts.demo
cd erp-console && npx tsc --noEmit && npm run build && NEXT_PUBLIC_USE_MOCK=1 npm run build
grep -rn "localStorage\|sessionStorage\|useDraft\|console\." erp-console/features/cskh erp-console/features/deliveries erp-console/app/print || true   # phải rỗng
grep -rn "features/ai" erp-console/features/cskh erp-console/features/deliveries erp-console/app/print || true            # phải rỗng
```
**Test bắt buộc:**
- CS-04-AC1…AC8 (AC2 cả Chủ xác nhận tay và hàng chờ lệch; AC5 ledger `CANCEL_RESTORE` đúng lô gốc; AC7 phiếu cũ không đổi).
- CS-05-AC1…AC9 (AC4 bằng `CSKH_CLAIM_MINUTES` và `now` giả; AC5 dòng ngoài phạm vi **không** có `customer_name`/`address`;
  AC6 `GET /api/cskh/search/?q=` → 405; search SĐT một phần → 400; throttle `cskh_search` N+1 → 429).
- CS-06-AC1…AC10 (AC6 các biến thể `0900.000.999`, `0900 000 999`, `+84900000999`, > 200 ký tự; AC8 cả nhánh tem đã in → 400).
- Luật UNREACHABLE/WRONG_NUMBER/CALLBACK của §1.4 ở mức service (đủ N, hết W, chưa đủ M → 400 `BR-GH-13`, WANT_* → ESCALATED
  không hạn) — AC đầy đủ nghiệm thu ở Lô 3 nhưng test service viết ngay lô này.
- CS-11-AC1…AC5, AC7 (JSON), AC8, AC9. AC6 (PDF 1 trang 100×150 ±1 mm) và giải mã QR: QA chạy Playwright Python
  (`page.pdf(prefer_css_page_size=True)`) trên mock.
- X-AC1, X-AC2 cho luồng CS-04…CS-11; X-AC3, X-AC6, X-AC7 cho endpoint của lô; header `Cache-Control: no-store`.

**Điều kiện xong:** lệnh sạch · QA APPROVED mục Lô 2 (gồm X-AC4 Playwright: storage/URL/console sạch; CS-05-AC8 mobile) ·
commit `Lô 2 CSKH: CS-04 chờ xác nhận, CS-05 hàng chờ gọi, CS-06 ghi kết quả, CS-11 tem 100x150` → `git push origin main`.
**Môi trường:** chỉ **staging**. Không lên production riêng Lô 2 (đơn có thể kẹt ở "Cần quyết định" khi chưa có `decide`) —
production cùng Lô 3.

---

## [x] Lô 3 — Không liên lạc được, tự huỷ, báo khách (QA APPROVED 2026-09-29)
> **Ràng buộc phát hành (bắt buộc):** Lô 3 **chỉ lên production sau khi `legal-vn` duyệt** câu `cancel_notice` và câu báo
> trước ở checkout (NĐ 356/2025), và Duy tự bật `CSKH_AUTO_CANCEL_ENABLED=1`. Code để mặc định `0`. Staging được bật `1` để
> QA. Chuỗi câu trong `customer_notices.py` và FE Shop giữ dấu `# CHỜ legal-vn` tới khi có bản duyệt; khi có, thay đúng câu,
> không đổi logic, chạy lại test CS-10.

**Việc (`02b` §4.4, §5, §7):**
- `decide` (DELIVER_WITHOUT_CONFIRM / EXTEND / CANCEL), khoá đơn → phiếu → task; `CANCEL` gọi `cancel_paid_order`; lý do
  `UNREACHABLE` cho người, `UNREACHABLE_AUTO` chỉ Hệ thống.
- `process_cskh_deadlines` (escalate + auto-cancel sau cờ), `check_cskh_job_health`; phiếu hoàn Hệ thống `created_by=NULL`,
  `request_id` uuid5; chặn `BR-LO-05` khi lô đã chốt; `REFUND_CALL` + `NOTIFIED`.
- Shop: `cancel_notice`, `status_label` khi `CONFIRMING`, `GET /api/public/site-info/` khoá `cskh_notice`; FE Shop hiện câu báo
  trước ở bước đặt/trang đặt xong (chỉ số từ API, câu huỷ chỉ khi `auto_cancel_enabled`), khối lý do huỷ ở tra đơn.
- ERP: khối "Cần quyết định" (3 lựa chọn, bắt buộc lý do), sau `CANCEL` chuyển `/orders/?order=<id>&open=refund`; lọc "Báo huỷ
  & hoàn" có số tiền, trạng thái hoàn, hạn, câu hướng dẫn D5; `Refund.created_by` null hiện "Hệ thống".
- Ghi vào `03-dev-notes.md` lệnh `gcloud` mẫu tạo Cloud Run Job + Scheduler `*/5` (không chạy).

**Lệnh kiểm chứng:**
```bash
cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run
cd backend && .venv/bin/python manage.py test apps.delivery apps.sales apps.reports
cd backend && .venv/bin/python manage.py process_cskh_deadlines && .venv/bin/python manage.py process_cskh_deadlines   # DB dev, dữ liệu giả: lần 2 "0"
cd backend && .venv/bin/python manage.py check_cskh_job_health; echo "exit=$?"
cd erp-console && npx tsc --noEmit && npm run build
cd frontend && npx tsc --noEmit && NEXT_PUBLIC_USE_MOCK=1 npm run build
```
**Test bắt buộc:**
- CS-07-AC1…AC12 (mốc giờ bằng `now=` / patch `timezone.now`; AC4 job chạy 2 lần không thêm AuditLog; AC6 đổi N).
- CS-08-AC1…AC11 (AC3 idempotent: 1 huỷ, 1 phiếu hoàn, 1 bút toán kho mỗi lô, 1 AuditLog `order_auto_cancelled`; AC6 hai
  thứ tự + kiểm thứ tự `select_for_update`; AC7 lô `CLOSED` → chặn, không log PII; AC9 báo cáo kỳ; AC10 WANT_* không huỷ;
  AC11 không có URL job) + **cờ tắt** → vẫn chuyển Quản lý, không huỷ.
- CS-09-AC1…AC8; CS-10-AC1…AC8 (AC1 đổi `CSKH_MAX_UNREACHABLE_ATTEMPTS=2` → câu "2 lần" không build lại FE; AC6 đệ quy
  không khoá PII; AC7 sai 4 số → 404 như cũ).
- X-AC1, X-AC2 cho job + decide; X-AC3 tra đơn + `site-info`; X-AC5 (`AI_ENABLED=false` và `true`: client AI mock gọi 0 lần).

**Điều kiện xong:** lệnh sạch · QA APPROVED mục Lô 3 (gồm E2E Shop mock: câu báo trước, tra đơn đã huỷ tự động) · commit
`Lô 3 CSKH: CS-07 chuyển Quản lý, CS-08 tự huỷ (cờ tắt), CS-09 nhắc gọi báo hoàn, CS-10 báo khách` → `git push origin main`.

---

## [x] Lô 4 — Hoàn thiện vận hành (CS-12, CS-13, CS-14, CS-15 làm song song được) (QA APPROVED 2026-09-29)
**Việc (`02b` §4.5):** đổi địa chỉ/người nhận (ghi đè `SalesOrder.delivery_address` qua service sales; người nhận hộ trên phiếu;
vô hiệu tem; AuditLog chỉ tên field); WANT_CANCEL/WANT_CHANGE với nhãn và câu hướng dẫn; in lại + huỷ tem + cảnh báo tem cũ/đơn
huỷ; `GET /api/dashboard/attention/` khoá theo quyền + khối trên Tổng quan (lỗi riêng khối).

**Lệnh kiểm chứng:**
```bash
cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run
cd erp-console && npx tsc --noEmit && npm run build && NEXT_PUBLIC_USE_MOCK=1 npm run build
grep -rn "localStorage\|sessionStorage\|useDraft\|console\." erp-console/features/cskh erp-console/features/deliveries erp-console/app/print || true   # phải rỗng
```
**Test bắt buộc:** CS-12-AC1…AC9 (AC6 tra đơn bằng 4 số cuối SĐT cũ vẫn được; AC7 quét địa chỉ cũ ở AuditLog + mọi bảng mới
→ không có); CS-13-AC1…AC5; CS-14-AC1…AC7; CS-15-AC1…AC6 (AC4 đúng tập khoá từng vai; `giao1` 403). X-AC1/2/3/6/7 cho endpoint
của lô.

**Điều kiện xong:** lệnh sạch · QA APPROVED mục Lô 4 · commit `Lô 4 CSKH: CS-12 đổi người nhận, CS-13 khách muốn huỷ/đổi,
CS-14 in lại/huỷ tem, CS-15 cần chú ý` → `git push origin main`.

---

## Lô 5 — Could (CS-16, CS-17, CS-18) — chỉ làm khi Duy bảo còn thời gian
**Việc (`02b` §4.6, §6):** trang `/print/pick-sheet/` không PII; `GET /api/delivery/notes/lookup/` + màn quét/gõ mã tem (cảnh
báo vàng tem cũ, đỏ đơn huỷ); model `CallScript` + migration + API (Chủ soạn, Quản lý/CSKH chỉ đọc) + hiện kịch bản trong chi
tiết gọi. Không AI.

**Lệnh kiểm chứng:** như Lô 4 (+ `makemigrations --check` sau migration mới).
**Test bắt buộc:** CS-16-AC1…AC4 (DOM không tên/SĐT/địa chỉ/người nhận hộ, không giá), CS-17-AC1…AC5, CS-18-AC1…AC4.
**Điều kiện xong:** QA APPROVED mục Lô 5 · commit `Lô 5 CSKH: CS-16 phiếu soạn, CS-17 quét tem, CS-18 kịch bản gọi` →
`git push origin main`.

---

## Mỗi lô: điều kiện xong (chung)
- Lệnh kiểm chứng của lô chạy **trong lượt đó**, dán output tóm tắt (số test, `No changes detected`, build OK) vào `03-dev-notes.md`.
- Test bắt buộc: phân quyền theo từng vai (ma trận X-AC7), không rò giá vốn (X-AC3), không rò dữ liệu cá nhân (X-AC1, X-AC2,
  X-AC4 khi lô có FE), AC mã theo bảng lô.
- QA APPROVED trong `04-qa-report.md` (mục của lô). Tối đa 2 vòng sửa theo workflow.
- `git status` không có `.env`, DB, ảnh chụp test, bí mật; đánh dấu ☑ + mã commit ở bảng Lô.
- **Không deploy.** Staging/production chỉ khi Duy nói rõ; Lô 2 chỉ staging; Lô 3 production sau `legal-vn` + Duy bật cờ.

## Điểm dừng hỏi Duy
- Contract/thiết kế không khớp code (vd vòng import không tránh được bằng import trong hàm, test cũ ngoài danh sách đỏ, cần đổi
  tên field/URL) → ghi "Lệch thiết kế" trong `03-dev-notes.md`, dừng lô; Tech Lead chốt lại `02b`.
- Bất kỳ việc nào đụng tiền (phiếu hoàn, doanh thu), giá vốn, phân quyền ngoài bảng §3.1, hoặc thêm field dữ liệu cá nhân
  ngoài `recipient_name`/`recipient_phone`.
- Cần gửi dữ liệu ra bên thứ ba (SMS, Zalo, dịch vụ in, CDN QR) hoặc thêm thư viện ngoài `qrcode`.
- Hồ sơ `sua-loi-bao-mat` chưa XONG / chưa merge `main`; hoặc hồ sơ khung go-live đã làm GL-01 với contract `site-info` khác
  §4.4 của `02b`.
- Câu chữ `legal-vn` đòi thêm trường trên tem hoặc đổi luật huỷ.
