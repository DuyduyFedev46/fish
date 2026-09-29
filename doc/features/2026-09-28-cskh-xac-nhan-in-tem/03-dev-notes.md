# Ghi chú phát triển — CSKH gọi xác nhận đơn → in tem → kho soạn hàng

- Bắt đầu: 2026-09-29
- Người thực hiện: Antigravity (Pair-programming cùng Duy)
- Số test BE gốc khi bắt đầu hồ sơ: **806 tests xanh 100%**.
- Nhánh thực hiện: `main`

---

## Lô 1 — Nền: Group `cskh`, phạm vi dữ liệu cá nhân, bảng + chi tiết phiếu giao (CS-01, CS-02, CS-03)
- Trạng thái: DEV HOÀN TẤT — CHỜ QA
- Phạm vi story: CS-01 (Group cskh, phạm vi PII), CS-02 (Bảng phiếu giao theo trạng thái), CS-03 (Chi tiết phiếu soạn & "Đã đóng gói").
- Sửa test cũ có chủ đích:
  - `backend/apps/delivery/tests/test_api.py::test_ac_ready_returns_full_note_json`: đổi người bấm `PREPARING -> READY` sang user `nv_kho` (CS-03-AC6: NV giao không soạn hàng, cần quyền `delivery.pack_deliverynote`).
  - `backend/apps/accounts/auth/tests/test_s47_me_labels.py`: cập nhật danh sách capabilities của Quản lý bao gồm 5 quyền mới của CSKH/giao hàng theo đúng bảng 02b §3.1 (`delivery.confirm_with_customer`, `delivery.change_recipient`, `delivery.decide_unconfirmed`, `delivery.pack_deliverynote`, `delivery.print_label`).

### 1. Backend đã làm:
- `backend/apps/common/pii.py`: `normalize_phone`, `mask_phone` (09xx xxx 123), `has_long_digit_run` (chặn chuỗi số ≥ 9 chữ số liên tiếp).
- `backend/apps/common/exceptions.py`: `ConflictError` (HTTP 409) và thuộc tính `extra` cho `BusinessError`.
- `backend/apps/common/api.py`: `NoStoreMixin` (gắn header `Cache-Control: no-store` cho endpoint PII) và cập nhật `exception_handler` hỗ trợ trích xuất `extra`.
- `backend/apps/delivery/models.py`:
  - `DeliveryNote`: thêm choice `Status.CONFIRMING`, 5 fields mới (`confirmed_at`, `confirmed_by`, `confirm_skipped`, `recipient_name`, `recipient_phone`), 5 custom permissions (`confirm_with_customer`, `change_recipient`, `decide_unconfirmed`, `pack_deliverynote`, `print_label`).
  - Thêm 3 models mới: `ConfirmationTask` (1-1 với note, state PENDING/CALLBACK/ESCALATED/REFUND_CALL/DONE), `CustomerCall` (append-only), `LabelPrint`.
- `backend/apps/delivery/migrations/0004_cskh_confirmation.py`: migration schema cho 3 model và field mới.
- `backend/apps/accounts/migrations/0011_seed_group_cskh.py`: data migration tạo Group `cskh`, gán quyền cho `cskh`, `quan_ly`, `nv_kho`, `chu` theo 02b §3.1 (idempotent, có reverse).
- `backend/apps/accounts/auth/services.py`:
  - `ROLE_ORDER` thêm `"cskh"`.
  - `GROUP_LABELS["cskh"] = "CSKH"`.
  - `CAPABILITY_LABELS` thêm 5 quyền delivery mới.
  - `home_for`: nếu nhóm `{"cskh"}` -> `"cskh-queue"`.
- `backend/config/settings.py`: thêm toàn bộ tham số CSKH (`CSKH_MAX_UNREACHABLE_ATTEMPTS`, `CSKH_PII_RECENT_DAYS`, `CSKH_CLAIM_MINUTES`, v.v.).
- `backend/apps/delivery/cskh/scope.py`: cài đặt `cskh_note_q`, `is_cskh`, `note_in_cskh_scope`.
- `backend/apps/sales/orders/api.py`: cập nhật `SalesOrderViewSet.get_queryset` tích hợp phạm vi `cskh_note_q` qua `Exists` và `.distinct()`.
- `backend/apps/delivery/services.py`:
  - `ALLOWED_TRANSITIONS` thêm `CONFIRMING: set()`, `CANCELLED: set()`.
  - `create_delivery_note`: hỗ trợ tham số `status=None` (mặc định `PREPARING`).
  - `advance_status`: hỗ trợ `from_status`, kiểm tra `BR-GH-11` (nếu CONFIRMING), `BR-GH-07` (nếu CANCELLED), `STALE_STATE` (nếu lệch from_status), trả về `(note, already: bool)`.
- `backend/apps/delivery/serializers.py`: `DeliveryNoteSerializer` và `DeliveryNoteDetailSerializer` (thêm `order`, `paid_at`, `lines_summary`, `total_kg`, `label`, `customer_name`, `address`, `available_actions`, `lines` kèm `expiry_date`, không rò giá vốn).
- `backend/apps/delivery/api.py`: `DeliveryNoteViewSet` hỗ trợ `StandardPagination`, `completed_from`, sắp xếp theo §4.2, action `set_status` kiểm tra quyền `delivery.pack_deliverynote` khi `to_status=READY`.
- `backend/apps/delivery/admin.py`: cập nhật `locked_fields`, `exclude=("recipient_name", "recipient_phone")`, đăng ký các model CSKH read-only.
- Test BE mới: `backend/apps/delivery/tests/test_cskh_l1.py` với 18 test cases bao phủ toàn diện CS-01 (AC1..AC7), CS-02 (AC1..AC7), CS-03 (AC1..AC6).
- Kết quả kiểm chứng BE:
  - `apps.delivery.tests`: 37/37 tests xanh.
  - `apps.delivery.tests.test_cskh_l1`: 18/18 tests xanh.
  - Toàn bộ backend suite: **824/824 tests xanh 100%**.
  - `makemigrations --check --dry-run`: No changes detected.
  - Fresh migrate kiểm tra tính idempotent: 2 lần liên tiếp chạy trơn tru, "No migrations to apply".

### 2. Frontend đã làm:
- `erp-console/shared/lib/groups.ts`: thêm `cskh: "CSKH"` vào `GROUP_LABEL`, `GROUP_CODES`, `GROUP_HINT`.
- `erp-console/shared/lib/nav.ts`: cập nhật `Viewer.home` thêm `"cskh-queue"`, cập nhật `homePath` định tuyến về `/cskh/queue/`, thêm `GROUP.cskh`.
- `erp-console/features/auth/types.ts`: thêm `"cskh"` vào `GroupCode` và `"cskh-queue"` vào `MeHome`.
- `erp-console/features/deliveries/`:
  - `types.ts`: khai báo đầy đủ các kiểu `DeliveryNoteItem`, `DeliveryNoteDetail`, `DeliveryLine`, `LabelInfo`, `DeliveryStatusGroup`, `STATUS_GROUP_TABS`.
  - `mock.ts`: dữ liệu mẫu cho các trạng thái `CONFIRMING`, `PREPARING`, `READY`, `DELIVERING`, `FAILED`, `COMPLETED`, không chứa giá vốn (bất biến 1), dùng dữ liệu giả (bất biến 9); các mock handler cho `apiFetch`.
  - `api.ts`: `fetchDeliveryNotes`, `fetchDeliveryNoteDetail`, `packDeliveryNote`.
  - `deliveries.module.css`: layout responsive cho cả Desktop (table) và Mobile (cards 360x640), badge trạng thái tem và phiếu, modal chi tiết phiếu.
  - `components/DeliveryDetailModal.tsx`: hiển thị chi tiết dòng hàng theo lô kèm HSD (CS-03-AC1), nút "Đã đóng gói" cho phiếu PREPARING có quyền (CS-03-AC2), xử lý `already: true` (CS-03-AC3) và lỗi.
  - `components/DeliveriesView.tsx`: màn hình quản lý giao hàng với các tab trạng thái, bảng desktop và thẻ mobile.
  - `deliveries.test.ts`: 9 vitest unit tests bao phủ CS-02, CS-03, X-AC3.
- `erp-console/app/(console)/deliveries/page.tsx`: tích hợp `DeliveriesView` thay thế cho Placeholder cũ.
- Kết quả kiểm chứng FE:
  - `cd erp-console && npm test`: 3 test files, 21/21 tests xanh.
  - `cd erp-console && npx tsc --noEmit && npm run build`: 25/25 static pages pass 100%.
  - `cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build`: 25/25 static pages pass 100%.
  - `cd frontend && npx tsc --noEmit && npm run build`: 8/8 static pages pass 100%.

---

## Lô 2 — Luồng xác nhận chạy được sớm nhất (gọi → xác nhận → in tem tay → soạn)
- Trạng thái: DEV HOÀN TẤT — CHỜ QA
- Phạm vi story:
  - CS-04: Đơn đã trả tiền vào "Chờ xác nhận", kho chưa soạn được.
  - CS-05: Hàng chờ gọi của CSKH, phân trang, lọc state, tìm kiếm bằng POST body, khoá mềm 5 phút chống tranh chấp.
  - CS-06: Ghi kết quả cuộc gọi (append-only), xác nhận chuyển PREPARING, huỷ xác nhận (unconfirm).
  - CS-11: Tem giao hàng khổ 100×150 mm in tay từ trình duyệt, QR code SVG trên client, tuyệt đối không tiền, không giá vốn, SĐT che.

### 1. Sửa test cũ có chủ đích (BR-GH-11):
- `backend/apps/common/tests/fixtures.py`:
  - `make_order_with_note` thêm tham số `confirmed=True` (mặc định) để mô phỏng đơn đã xác nhận (chuyển PREPARING và task DONE), giữ cho các test cũ đi qua fixture không bị ảnh hưởng.
  - Thêm helper `confirm_note_for_test(note, user=None, confirmed_at=None)` và `make_confirming_note(order=None, ...)`.
- Test đi qua luồng thanh toán thật chuyển kỳ vọng sang `CONFIRMING` hoặc dùng `confirm_note_for_test`:
  - `backend/apps/sales/orders/tests/test_s10_api.py`
  - `backend/apps/sales/orders/tests/test_l7_bosung.py`
  - `backend/apps/sales/orders/tests/test_f1_fefo.py`
  - `backend/apps/sales/orders/tests/test_s14_cancel_paid_order.py`
  - `backend/apps/sales/payments/tests/test_p3_sepay_gateway_ipn.py`
  - `backend/apps/sales/payments/tests/test_s11_confirm_manual.py`
  - `backend/apps/sales/payments/tests/test_s12_payment_queue.py`
  - `backend/apps/sales/orders/tests/test_s9_admin_locked_fields.py`
  - `backend/apps/delivery/tests/test_cskh_l1.py`
  - `backend/apps/ai/registry/tests/test_discipline.py`: cập nhật tổng số custom actions từ 19 lên 21 (thêm `label` và `label_print` trên `DeliveryNoteViewSet`).

### 2. Backend đã làm:
- `backend/config/settings.py` & `backend/apps/common/throttling.py`:
  - Thêm `CskhSearchThrottle` (khoá theo user id, rate `THROTTLE_CSKH_SEARCH` = `30/min`).
  - Cấu hình tham số CSKH: `CSKH_CLAIM_MINUTES = 5`, `CSKH_MAX_UNREACHABLE_ATTEMPTS = 3`, `CSKH_UNREACHABLE_WINDOW_MINUTES = 30`, `CSKH_MIN_RETRY_MINUTES = 10`.
- `backend/apps/delivery/signals.py`:
  - Nối `start_confirmation(invoice)` vào tín hiệu `SalesInvoice.Status.ISSUED` tạo `CONFIRMING` note + `ConfirmationTask` trong cùng 1 transaction, idempotent chống lặp IPN.
- `backend/apps/sales/orders/services.py`:
  - `_STOCK_STILL_IN_WAREHOUSE` thêm `DeliveryNote.Status.CONFIRMING`.
  - `cancel_paid_order` gọi `close_task_on_cancel(note)` đưa task về `DONE`.
- `backend/apps/delivery/cskh/services.py`:
  - `claim_task`: khoá mềm trong 5 phút (`CSKH_CLAIM_MINUTES`), trả 409 `CLAIMED` nếu có người khác đang giữ.
  - `record_call`: máy trạng thái CONFIRMED, CALLBACK, UNREACHABLE, WRONG_NUMBER, WANT_CANCEL, WANT_CHANGE, NOTIFIED. Kiểm tra BR-GH-19 (chặn SĐT/STK trong ghi chú), BR-GH-13 (giãn cách 10' nếu chưa đủ N/W), thứ tự khoá `DeliveryNote` -> `ConfirmationTask`. Ghi AuditLog an toàn không lưu ghi chú tự do.
  - `unconfirm`: đưa phiếu PREPARING về CONFIRMING khi chưa in tem (chặn 400 `BR-GH-16` nếu đã in tem).
  - `change_recipient`: đổi người nhận hộ, cập nhật `superseded_at = now` vô hiệu hoá tem cũ.
- `backend/apps/delivery/labels/services.py`:
  - `get_label_data`: sinh dữ liệu tem (tuyệt đối không giá vốn, không tiền, SĐT che dạng `09xx xxx 123`, barcode_value `f"{note.code}.{print_no}"`, chặn khi CONFIRMING BR-GH-09 hoặc CANCELLED BR-GH-07 hoặc tem cũ superseded BR-GH-16).
  - `record_print`: idempotent theo `request_id`, tăng `print_no`, AuditLog `label_printed` / `label_reprinted`.
- `backend/apps/delivery/cskh/serializers.py` & `api.py`:
  - `CskhQueueViewSet`: list (mặc định PENDING + CALLBACK hợp lệ, lọc `?state=`), detail (404 nếu ngoài scope), custom actions `claim`, `calls`, `unconfirm`, `recipient`. Header `Cache-Control: no-store`.
  - `CskhSearchView`: chỉ nhận POST (GET trả 405), throttle `cskh_search`, tìm đúng SĐT ≥ 9 chữ số hoặc mã đơn, chặn SĐT một phần (400 `INVALID_QUERY`).
- `backend/apps/delivery/api.py`:
  - Thêm custom actions `label` (GET) và `label_print` (POST `.../label/print/`), kế thừa `NoStoreMixin`.
- `backend/config/api_urls.py`: Đăng ký router `/api/cskh/queue/` và view `/api/cskh/search/`.
- `backend/apps/accounts/management/commands/seed_demo.py`: Cập nhật `adopt_legacy()` nhận `CONFIRMING` và dọn `confirmation`, `calls`, `label_prints` khi `--remove`.
- Test BE mới: `backend/apps/delivery/tests/test_cskh_l2.py` với 19 tests bao phủ CS-04 (AC1..AC8), CS-05 (AC1..AC9), CS-06 (AC1..AC10), CS-11 (AC1..AC5, AC7..AC9), X-AC1, X-AC2, X-AC3.

### 3. Frontend đã làm:
- `erp-console/package.json`: thêm `qrcode` (`^1.5.4`) và `@types/qrcode` (`^1.5.5`).
- `erp-console/shared/lib/nav.ts`:
  - Thêm `cskh` vào `ViewKey`.
  - Thêm quyền CSKH vào `PERM` (`confirmWithCustomer`, `changeRecipient`, `printLabel`, `decideUnconfirmed`, `packDeliveryNote`).
  - Thêm mục menu "Gọi xác nhận" (`/cskh/`, icon `phone_in_talk`, hiển thị khi có `confirmWithCustomer`).
  - Cập nhật `homePath` trả về `/cskh/` khi `me.home === "cskh-queue"`.
- `erp-console/features/orders/labels.ts`: thêm `CONFIRMING: "Chờ xác nhận"` vào `DELIVERY_LABEL` và `DELIVERY_STATUS`.
- `erp-console/features/deliveries/`:
  - `types.ts`: thêm `LabelData`, `PrintDeliveryLabelResponse`.
  - `api.ts`: thêm `fetchDeliveryLabel`, `printDeliveryLabel`.
  - `mock.ts`: thêm `mockGetDeliveryLabel`, `mockPostDeliveryLabelPrint`.
  - `components/DeliveryDetailModal.tsx`: thêm nút "In tem" / "In lại tem", gọi API in và mở popup `/print/label/?note={id}&print_no={n}`.
- `erp-console/app/print/label/page.tsx`:
  - Màn hình in tem nhãn giao hàng độc lập (ngoài console layout).
  - Khổ giấy CSS `@page { size: 100mm 150mm; margin: 0; }`.
  - Sinh mã QR client-side qua SVG bằng thư viện `qrcode`.
  - Đảm bảo bất biến: Tuyệt đối không giá tiền, không giá vốn, SĐT che `09xx xxx 123`, tự động gọi `window.print()` sau khi render.
- `erp-console/features/cskh/`:
  - `types.ts`: các kiểu dữ liệu `CskhQueueItem`, `CustomerCall`, `CskhQueueDetail`, `CskhSearchResultItem`, options kết quả gọi.
  - `mock.ts`: dữ liệu mẫu hàng chờ, cuộc gọi, tìm kiếm, khoá mềm, đổi người nhận, huỷ xác nhận.
  - `api.ts`: các hàm `fetchCskhQueue`, `fetchCskhDetail`, `claimCskhTask`, `recordCskhCall`, `unconfirmDelivery`, `changeRecipient`, `searchCskh`.
  - `cskh.module.css`: phong cách Linear/Notion tối giản, responsive mobile (nút kết quả to ≥ 44px ở nửa dưới màn hình).
  - `CskhCallModal.tsx`: modal gọi xác nhận, tự động claim task khi mở, hiển thị SĐT link `tel:`, ghi chú kiểm tra BR-GH-19, lưới nút kết quả, lịch sử gọi.
  - `CskhQueueView.tsx`: màn hình hàng chờ CSKH với các tab lọc trạng thái, tìm kiếm POST body, bảng desktop & thẻ mobile.
  - `cskh.test.ts`: 14 vitest unit tests bao phủ các AC của CS-05, CS-06, CS-11, X-AC3.
- `erp-console/app/(console)/cskh/page.tsx`: trang route `/cskh/` bọc `ViewGuard view="cskh"`.

### 4. Kết quả kiểm chứng Lô 2:
- `cd backend && .venv/bin/python manage.py test`: **843/843 tests xanh 100%** (38/38 tests delivery, 19/19 test_cskh_l2).
- `cd backend && .venv/bin/python manage.py makemigrations --check --dry-run`: No changes detected.
- `cd erp-console && npm test`: 4 test files, **35/35 tests xanh 100%**.
- `cd erp-console && npx tsc --noEmit && npm run build`: 27/27 static pages pass 100%.
- `cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build`: 27/27 static pages pass 100%.
- `cd frontend && npx tsc --noEmit && npm run build`: 8/8 static pages pass 100%.
- Quét cấm storage, useDraft, console: `grep -rn "localStorage\|sessionStorage\|useDraft\|console\." erp-console/features/cskh erp-console/features/deliveries erp-console/app/print` -> **Rỗng 100%**.
- Quét cấm AI import: `grep -rn "features/ai" erp-console/features/cskh erp-console/features/deliveries erp-console/app/print` -> **Rỗng 100%**.
