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

---

## Lô 3 — Không liên lạc được, tự huỷ, báo khách (CS-07, CS-08, CS-09, CS-10)
- Trạng thái: DEV HOÀN TẤT — CHỜ QA
- Phạm vi story:
  - CS-07: Không liên lạc được: 3 lần trong 30 phút rồi chuyển Quản lý quyết định (giao luôn / gia hạn / huỷ).
  - CS-08: Hệ thống tự huỷ khi Quản lý không xử lý trong 30 phút (`CSKH_AUTO_CANCEL_ENABLED` mặc định 0, bật trên staging/test). Phiếu hoàn `created_by=None` (Hệ thống). Chặn `BR-LO-05` khi lô đã `CLOSED`.
  - CS-09: Nhắc việc gọi khách báo huỷ và hoàn tiền (`REFUND_CALL`), hướng dẫn D5 không ghi STK vào hệ thống.
  - CS-10: Shop báo trước luật gọi xác nhận và báo lý do, số tiền hoàn khi đơn bị tự huỷ (`cancel_notice`, `# CHỜ legal-vn`).

### 1. Sửa test cũ có chủ đích (02b §4.4):
- `backend/apps/sales/orders/tests/test_l6_lookup.py`:
  - `test_s02_ac3_khong_ro_khoa_nhay_cam`: API tra đơn trước đây có đúng 7 khoá, nay bổ sung khoá thứ 8 là `cancel_notice` (chứa lý do huỷ và thông tin hoàn tiền khi đơn CANCELLED, null khi đơn đang xử lý). Test được cập nhật chấp nhận đúng 8 khoá theo thiết kế §4.4.

### 2. Backend đã làm:
- `backend/apps/sales/models/refunds.py`:
  - `Refund.created_by`: đổi thành `null=True, blank=True` để cho phép Hệ thống tự lập phiếu hoàn tiền (CS-08).
- `backend/apps/sales/migrations/0007_alter_refund_created_by.py`:
  - Migration nới lỏng ràng buộc `created_by` của `Refund`.
- `backend/config/settings.py`:
  - Thêm `CSKH_NOTICE_ENABLED = _bool("CSKH_NOTICE_ENABLED", "1")`.
  - Thêm `CSKH_AUTO_CANCEL_ENABLED = _bool("CSKH_AUTO_CANCEL_ENABLED", "0")` (mặc định tắt theo yêu cầu an toàn).
  - Thêm `CSKH_MANAGER_DECISION_MINUTES = int(os.environ.get("CSKH_MANAGER_DECISION_MINUTES", "30"))`.
  - Thêm `CSKH_EXTEND_MAX_HOURS = int(os.environ.get("CSKH_EXTEND_MAX_HOURS", "24"))`.
  - Thêm `REFUND_DEADLINE_DAYS = int(os.environ.get("REFUND_DEADLINE_DAYS", "30"))`.
  - Thêm `SHOP_WORKING_HOURS = os.environ.get("SHOP_WORKING_HOURS", "07:00-21:00")`.
- `backend/apps/sales/orders/services.py`:
  - Thêm `"UNREACHABLE": "Không liên lạc được khách"` vào `CANCEL_REASON_LABELS`.
  - Thêm `SYSTEM_CANCEL_REASON_CODES = {"UNREACHABLE_AUTO": "Hệ thống tự huỷ — không liên lạc được"}`.
  - Cập nhật `ALL_CANCEL_REASON_CODES` kết hợp cả 2 bộ mã.
- `backend/apps/sales/orders/customer_notices.py`:
  - Dựng template thông điệp tự huỷ động theo `CSKH_MAX_UNREACHABLE_ATTEMPTS` và `CSKH_UNREACHABLE_WINDOW_MINUTES` kèm `# CHỜ legal-vn`.
  - Hàm `build_cancel_notice(order)` tổng hợp trạng thái hoàn tiền, hạn hoàn (`created_at + 30 ngày`) và hotline.
- `backend/apps/sales/orders/shop_api.py`:
  - `ShopOrderLookupView` trả `cancel_notice` khi đơn CANCELLED (hoặc null), trả `status_label = "Đã thanh toán – chờ vựa gọi xác nhận"` khi `CONFIRMING`.
- `backend/apps/common/site_info_api.py`:
  - Cung cấp `GET /api/public/site-info/` (AllowAny, public Cache-Control 300s, chứa khoá `cskh_notice`).
- `backend/config/api_urls.py`:
  - Đăng ký endpoint `path("public/site-info/", PublicSiteInfoView.as_view())`.
- `backend/apps/delivery/cskh/services.py`:
  - `decide`: khoá 3 tầng (`SalesOrder` -> `DeliveryNote` -> `ConfirmationTask`). Hỗ trợ `DELIVER_WITHOUT_CONFIRM` (chuyển PREPARING, AuditLog `delivery_confirm_skipped`), `EXTEND` (về CALLBACK, chặn > 24h BR-GH-13), `CANCEL` (gọi `cancel_paid_order`, trả `suggest_refund_amount`).
  - `escalate_expired_windows`: chuyển các task PENDING hết cửa sổ 30 phút sang ESCALATED, idempotent.
  - `auto_cancel_overdue`: kiểm tra cờ `CSKH_AUTO_CANCEL_ENABLED`. Kiểm tra lô `CLOSED` (chặn `BR-LO-05`, ghi AuditLog `order_auto_cancel_blocked`). Huỷ đơn tự động với lý do `UNREACHABLE_AUTO`, tạo `Refund(created_by=None)` idempotent qua UUID5, chuyển task sang `REFUND_CALL`, ghi AuditLog `order_auto_cancelled` với `actor=None`.
  - Cho phép `claim_task` và `record_call` thao tác trên phiếu CANCELLED khi `task.state == "REFUND_CALL"`.
- `backend/apps/delivery/cskh/serializers.py`:
  - Cập nhật `decide_deadline` (trả null khi WANT_CANCEL/WANT_CHANGE).
  - Trả thông tin `refund` và `cancelled_at` khi task ở trạng thái `REFUND_CALL`.
- `backend/apps/delivery/cskh/api.py`:
  - Action `decide` trên `CskhQueueViewSet` yêu cầu quyền `delivery.decide_unconfirmed`.
- `backend/apps/delivery/management/commands/process_cskh_deadlines.py`:
  - Command định kỳ quét và xử lý escalate + auto-cancel.
- `backend/apps/delivery/management/commands/check_cskh_job_health.py`:
  - Command giám sát sức khoẻ job (exit code 1 khi có task quá hạn treo, exit code 0 khi khoẻ).
- Test BE mới: `backend/apps/delivery/tests/test_cskh_l3.py`:
  - **37 test cases** bao phủ toàn diện CS-07 (AC1..AC12), CS-08 (AC1..AC11), CS-09 (AC1..AC8), CS-10 (AC1..AC8) và các bất biến.

### 3. Frontend đã làm:
- `erp-console/features/cskh/`:
  - `types.ts`: thêm `CskhDecision`, `DecidePayload`, `DecideResponse`, trường `refund`, `cancelled_at`, `guidance` vào `CskhQueueItem` và `CskhQueueDetail`. Thêm `NOTIFIED` vào `CALL_RESULT_OPTIONS`.
  - `api.ts`: thêm hàm `decideCskh`.
  - `mock.ts`: bổ sung mock items ESCALATED (note 28) và REFUND_CALL (note 27), hàm `mockDecideCskh`, cho phép gọi khi `REFUND_CALL`.
  - `CskhCallModal.tsx`:
    - Khối "Cần quyết định (Quản lý)": 3 lựa chọn (Giao không xác nhận, Gia hạn, Huỷ đơn kèm form). Bấm Huỷ đơn thành công tự động điều hướng sang `/orders/?order=${res.order_id}&open=refund`.
    - Khối REFUND_CALL: banner D5 ("Không ghi số tài khoản khách vào hệ thống..."), thông tin hoàn tiền (`refund`), 2 nút kết quả (`NOTIFIED` / `UNREACHABLE`).
  - `CskhQueueView.tsx`:
    - Banner D5 trên tab "Báo hoàn tiền".
    - Hiển thị thông tin hoàn tiền (`item.refund`) trên các thẻ đơn hàng.
  - `cskh.test.ts`: thêm 5 vitest unit tests cho Lô 3 (CS-07, CS-09).
- `erp-console/features/orders/`:
  - `OrderDetailSheet.tsx`: thêm prop `initialMode` để mở sẵn form hoàn tiền (`mode="refund"`).
  - `OrdersScreen.tsx`: bắt query param `?order=<id>&open=refund` tự động mở chi tiết đơn và mở sẵn form hoàn tiền.
  - `RefundView.tsx` & `RefundQueueScreen.tsx`: hiển thị "Hệ thống" khi `created_by` là null.
- `frontend/lib/`:
  - `types.ts`: thêm `CskhNoticeConfig`, `SiteInfo`, `OrderCancelNotice`. Cập nhật `OrderStatus` và `WireOrderStatus` hỗ trợ `cancel_notice` và `fulfilment`.
  - `api.ts`: thêm hàm `getSiteInfo()`, cập nhật `mapOrderStatus`.
  - `mock.ts`: thêm đơn mẫu `DH-DEMO004` (đơn tự huỷ kèm `cancel_notice` và `refund`), thêm `mockGetSiteInfo()`.
- `frontend/app/shop/orders/OrderLookup.tsx`:
  - Hiển thị khối `cancel_notice` (lý do huỷ, số tiền hoàn, trạng thái hoàn, hạn hoàn/ngày đã hoàn, hotline) khi đơn bị huỷ.
- `frontend/features/checkout/components/CheckoutScreen.tsx` & `PaymentPanel.tsx`:
  - Tải `getSiteInfo()` và hiển thị câu thông báo lưu ý luật gọi xác nhận đơn trước khi đặt và sau khi đặt thành công (kèm dấu `# CHỜ legal-vn`).

### 4. Lệnh gcloud mẫu tạo Cloud Run Job + Cloud Scheduler (tham khảo hạ tầng, KHÔNG CHẠY):
```bash
# 1. Tạo Cloud Run Job quét deadline CSKH (chạy container backend django)
gcloud run jobs create cskh-deadlines-job \
  --image asia-southeast1-docker.pkg.dev/<PROJECT_ID>/cangca/backend:latest \
  --region asia-southeast1 \
  --command "python" \
  --args "manage.py,process_cskh_deadlines" \
  --set-env-vars "DJANGO_SETTINGS_MODULE=config.settings" \
  --service-account "cloud-run-jobs@<PROJECT_ID>.iam.gserviceaccount.com"

# 2. Tạo Cloud Scheduler định kỳ mỗi 5 phút gọi Cloud Run Job
gcloud scheduler jobs create http cskh-deadlines-scheduler \
  --location asia-southeast1 \
  --schedule "*/5 * * * *" \
  --time-zone "Asia/Ho_Chi_Minh" \
  --uri "https://asia-southeast1-run.googleapis.com/v2/projects/<PROJECT_ID>/locations/asia-southeast1/jobs/cskh-deadlines-job:run" \
  --http-method POST \
  --oauth-service-account-email "cloud-scheduler@<PROJECT_ID>.iam.gserviceaccount.com"
```

### 5. Kết quả kiểm chứng Lô 3:
- `cd backend && .venv/bin/python manage.py makemigrations --check --dry-run`: **No changes detected**.
- `cd backend && .venv/bin/python manage.py test apps.delivery apps.sales apps.reports`: **361/361 tests xanh 100%** (trong đó có 37 tests của `test_cskh_l3.py`).
- `cd backend && .venv/bin/python manage.py test`: **880/880 tests xanh 100%** (toàn bộ test suite backend).
- `cd backend && .venv/bin/python manage.py process_cskh_deadlines && .venv/bin/python manage.py process_cskh_deadlines`: Cả 2 lần đều trả về 0, idempotent, không lỗi.
- `cd backend && .venv/bin/python manage.py check_cskh_job_health; echo "exit=$?"`: **exit=0**.
- `cd erp-console && npm test`: 4 test files, **40/40 tests xanh 100%**.
- `cd erp-console && npx tsc --noEmit && npm run build`: **27/27 static pages pass 100%**.
- `cd frontend && npx tsc --noEmit && NEXT_PUBLIC_USE_MOCK=1 npm run build`: **8/8 static pages pass 100%**.

---

## Lô 4 — Hoàn thiện vận hành (CS-12, CS-13, CS-14, CS-15)

### 1. Phạm vi thực hiện:
- **CS-12**: Đổi địa chỉ / người nhận hộ (AC1..AC10).
- **CS-13**: Khách muốn huỷ / đổi món (AC1..AC8).
- **CS-14**: In lại tem, tem hết hiệu lực, xác nhận đã huỷ tem giấy (AC1..AC7).
- **CS-15**: "Cần chú ý" cho việc gọi và tem trên dashboard (AC1..AC6).

### 2. Backend đã làm:
- `backend/apps/sales/orders/services.py`:
  - Thêm `update_delivery_address(order, address)` ghi đè `order.delivery_address` (không sửa `phone` hay `Customer.default_address`).
- `backend/apps/delivery/cskh/services.py`:
  - Nâng cấp `change_recipient` hỗ trợ: `delivery_address`, `recipient_name`, `recipient_phone`.
  - Validate SĐT 10 số bắt đầu bằng 0 (`BR-BH-14`), địa chỉ không rỗng và <= 500 ký tự.
  - Chặn khi phiếu `READY`/`DELIVERING` (400 `BR-GH-15`), `CANCELLED` (400 `BR-GH-07`).
  - Vô hiệu tem cũ (`superseded_at = now`) khi có thay đổi trên phiếu đã in tem, trả `label_invalidated: True`.
  - AuditLog `recipient_changed` chỉ lưu `{"fields": changed_fields}` (Bất biến 9).
- `backend/apps/delivery/cskh/api.py`:
  - `recipient` action nhận `delivery_address`, trả về `changed` và `label_invalidated`.
  - Kiểm tra quyền `delivery.change_recipient` (403 cho `kho1`, `giao1`) và scope 404 cho CSKH ngoài scope.
- `backend/apps/delivery/cskh/serializers.py`:
  - Map `escalation_label` chuẩn spec: `"Khách muốn đổi món – huỷ + hoàn + đặt lại"` khi `WANT_CHANGE`, `"Khách muốn huỷ"` khi `WANT_CANCEL`.
- `backend/apps/delivery/labels/services.py`:
  - Trong `record_print`: khi in lại (`next_print_no > 1`), đánh dấu `superseded_at = now` cho các tem trước đó chưa superseded.
  - Thêm hàm `void_label(note, user, print_no)`: huỷ tem giấy, idempotent (trả `already: True` nếu đã void), chặn huỷ tem đang có hiệu lực duy nhất 400 `BR-GH-16`, AuditLog `label_voided`.
- `backend/apps/delivery/api.py`:
  - Thêm action `label_void` trên `DeliveryNoteViewSet` (`POST /api/delivery/notes/{id}/label/void/`).
  - Cập nhật `custom_perm_actions = ("set_status", "label", "label_print", "label_void")`.
- `backend/apps/delivery/attention_api.py` & `backend/config/api_urls.py`:
  - Thêm endpoint `GET /api/dashboard/attention/`: trả 6 khoá lọc theo quyền: `cskh_queue_waiting`, `refund_calls_open` (`confirm_with_customer`), `cskh_escalated`, `cskh_auto_cancel_blocked` (`decide_unconfirmed`), `labels_not_printed`, `labels_to_void` (`print_label`). User không có quyền nào (như `giao1`) trả 403.
- `backend/apps/ai/policy/rules.py`:
  - Cập nhật `FORBIDDEN_PREFIXES` thêm `/api/dashboard/attention/`.
  - Cập nhật `FORBIDDEN_SUFFIXES` thêm `/label/void/`, `/label/void`.
- Test BE mới: `backend/apps/delivery/tests/test_cskh_l4.py`:
  - **27 test cases** bao phủ toàn diện CS-12, CS-13, CS-14, CS-15, ma trận quyền và các bất biến.

### 3. Frontend đã làm:
- `erp-console/features/cskh/`:
  - `CskhCallModal.tsx`:
    - Hiển thị thông báo `notice` ("Tem cũ đã hết hiệu lực – cần in lại tem mới và huỷ tem cũ.") khi đổi người nhận/địa chỉ trên đơn đã in tem.
    - Hiển thị hướng dẫn khi `ESCALATED` theo đúng `escalation_reason`:
      - `WANT_CHANGE`: 💡 **Khách muốn đổi món:** Quản lý huỷ đơn và tạo phiếu hoàn tiền. Mời khách đặt đơn mới trên Shop sau khi đơn cũ được huỷ.
      - `WANT_CANCEL`: 💡 **Khách muốn huỷ đơn:** Quản lý huỷ đơn và lập phiếu hoàn tiền cho khách.
- `erp-console/features/deliveries/`:
  - `types.ts`: thêm kiểu `VoidLabelResponse`.
  - `api.ts`: thêm hàm `voidDeliveryLabel`.
  - `mock.ts`: thêm `mockPostDeliveryLabelVoid`, cập nhật `mockPostDeliveryLabelPrint` đưa tem cũ vào `to_void` khi reprint.
  - `components/DeliveryDetailModal.tsx`:
    - Danh sách tem cần huỷ theo `current.label.to_void`:
      - Đơn `CANCELLED`: hiện banner đỏ `🚨 Đơn đã huỷ – xé tem lần {pNo}`.
      - Đơn hoạt động: hiện banner vàng `⚠️ Tem cũ lần {pNo} hết hiệu lực – in tem mới, huỷ tem cũ`.
    - Nút "Đã huỷ tem" gọi `voidDeliveryLabel` và cập nhật lại state.
  - `deliveries.test.ts`: thêm unit test cho reprint và void label.
- `erp-console/features/overview/`:
  - `types.ts`: thêm kiểu `DashboardAttentionData`.
  - `api.ts`: thêm hàm `getDashboardAttention()`.
  - `mock.ts`: thêm `mockAttention` phân quyền 3 tầng theo quyền thật của BE.
  - `components/AttentionBlock.tsx`: component tải và hiển thị 6 đầu việc cần chú ý; xử lý lỗi riêng khối ("Chưa tải được" theo CS-15-AC6); link điều hướng trực tiếp sang `/cskh/` và `/deliveries/`.
  - `components/OverviewScreen.tsx`: nhúng `<AttentionBlock />` vào khối "Cần chú ý".
  - `overview.test.ts`: unit test phân quyền `mockAttention` cho Quản lý, CSKH, Kho, Giao hàng (403).

### 4. Kết quả kiểm chứng Lô 4:
- `cd backend && .venv/bin/python manage.py makemigrations --check --dry-run`: **No changes detected**.
- `cd backend && .venv/bin/python manage.py test apps.delivery apps.ai.registry.tests`: **145/145 tests xanh 100%**.
- `cd backend && .venv/bin/python manage.py test`: **907/907 tests xanh 100%** (toàn bộ test suite backend).
- `cd erp-console && npm test`: 5 test files, **42/42 tests xanh 100%**.
- `cd erp-console && npx tsc --noEmit && npm run build`: **27/27 static pages pass 100%**.
- `cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build`: **27/27 static pages pass 100%**.
- `cd frontend && npx tsc --noEmit && NEXT_PUBLIC_USE_MOCK=1 npm run build`: **8/8 static pages pass 100%**.
- `grep -rn "localStorage\|sessionStorage\|useDraft\|console\." erp-console/features/cskh erp-console/features/deliveries erp-console/app/print || true`: **Rỗng** (Bất biến 9).
- `grep -rn 'fields = "__all__"' backend/apps/delivery backend/apps/common/pii.py erp-console/features/deliveries || true`: **Rỗng**.


---

## Lô 5 — BE (CS-16, CS-17, CS-18) — nhánh `feat/cskh-lo5`

### 1. Đã làm (BE)
- **CS-16**: không cần API mới (02b §4.6). Phiếu soạn dùng `GET /api/delivery/notes/{id}/` như CS-03; FE tự ẩn tên, SĐT, địa chỉ, người nhận hộ, giá khi in.
- **CS-17** `GET /api/delivery/notes/lookup/?code=<mã tem>` (action `lookup` của `DeliveryNoteViewSet`, `detail=False`). Quyền `delivery.print_label` (Chủ, Quản lý, Kho có; CSKH và Giao 403, chưa đăng nhập 401). Có `Cache-Control: no-store`.
- **CS-18** model `CallScript` + `/api/confirmation/scripts/` + khoá `scripts` trong chi tiết hàng chờ.

### 2. Contract thực tế cho FE (dữ liệu giả)
```
GET /api/delivery/notes/lookup/?code=GH-HD-0001-AB12C.1
200 {"note_id": 31, "status": "PREPARING", "print_no": 1, "valid_print_no": 2, "warning": "BR-GH-16"}
    warning: null | "BR-GH-16" (tem cũ/đã huỷ tem, valid_print_no = lần hiệu lực) | "BR-GH-07" (phiếu CANCELLED, valid_print_no = null)
404 {"detail": "Không tìm thấy phiếu.", "code": "NOT_FOUND"}     # phiếu không có, hoặc phiếu có nhưng chưa từng in lần đó
400 {"detail": "Mã tem không đúng định dạng.", "code": "INVALID_INPUT"}   # regex ^GH-[A-Z0-9-]{3,40}\.\d{1,3}$, thiếu code cũng 400
```
Phản hồi **không** có tên, SĐT, địa chỉ, mã đơn, giá; lỗi không lặp lại giá trị đã gửi.

```
GET /api/confirmation/scripts/            (view_callscript: Chủ, Quản lý, CSKH)
200 {"results": [{"situation": "FIRST_ORDER", "situation_label": "Khách mua lần đầu", "content": "Chào anh/chị, em gọi từ Cá Về…", "is_active": true}]}
    Người có change_callscript (Chủ) thấy cả kịch bản đã tắt; Quản lý/CSKH chỉ thấy is_active=true.
POST /api/confirmation/scripts/  {"situation": "FIRST_ORDER", "content": "…", "is_active": true}      (add_callscript: Chủ)
201 {…như trên…}    400 nếu situation sai/đã có, nội dung rỗng hoặc > 2000 ký tự, hoặc có chuỗi ≥ 9 chữ số (code BR-GH-19)
PATCH /api/confirmation/scripts/FIRST_ORDER/  {"is_active": false}  hoặc {"content": "…"}   (change_callscript: Chủ)
200 {…}   404 nếu chưa có kịch bản tình huống đó.   DELETE/PUT → 405 (không xoá, tắt bằng is_active)
```
Tình huống (`situation`): `FIRST_ORDER` "Khách mua lần đầu", `RETURNING` "Khách quen", `COMBO` "Đơn có combo", `GENERAL` "Lời dặn chung".

```
GET /api/confirmation/queue/31/  → thêm "scripts": [{"situation": "FIRST_ORDER", "situation_label": "Khách mua lần đầu", "content": "…"}]
```
Chọn kịch bản (chỉ khi user có `delivery.view_callscript`, nếu không là `[]`): `FIRST_ORDER` nếu khách chưa có đơn PROCESSING/COMPLETED nào khác, ngược lại `RETURNING`; thêm `COMBO` nếu có dòng đơn có `bundle_snapshot`; luôn thêm `GENERAL` nếu bật. Chỉ kịch bản `is_active`. Thứ tự: FIRST_ORDER/RETURNING, COMBO, GENERAL.

### 3. Migration
- `delivery/0008_callscript`: `CreateModel CallScript` (`situation` unique, `content`, `is_active`, `updated_by` PROTECT, `updated_at`; `default_permissions = (view, add, change)`).
- `delivery/0009_grant_callscript` (data migration, **nằm ở app `delivery`, không tạo migration `accounts/`** nên không trùng số với việc phạm vi dữ liệu): `owner` view+add+change; `manager`, `customer_service` chỉ view; Kho, Giao không có. Dùng `add` nên chạy lại không đổi gì; có `reverse`.

### 4. Luật đã cài
BR-GH-16 (tem cũ), BR-GH-07 (đơn huỷ), BR-GH-19 (kịch bản không chứa chuỗi số dài, tức không dữ liệu cá nhân), BR-PQ-02/12 (Chủ soạn, Quản lý/CSKH chỉ đọc). `AuditLog` ghi `create_callscript` và `update_callscript` (model `delivery.CallScript`); `changes` chỉ có tình huống, cờ bật/tắt và `content_changed: true`, **không chép nội dung**. Không có đường nào gọi AI (test chạy với `AI_ENABLED=False`, X-AC5).

### 5. File
Sửa: `backend/apps/delivery/models.py`, `delivery/api.py` (action `lookup`), `delivery/confirmation/serializers.py` (khoá `scripts`), `backend/config/api_urls.py` (route scripts). Mới: `delivery/confirmation/call_scripts.py` (service), `delivery/confirmation/scripts_api.py` (viewset), 2 migration trên, `delivery/tests/test_call_scripts_and_lookup.py` (33 test: AC mã CS-17-AC1…5, CS-18-AC1…4, PII, 5 vai, audit, X-AC5).
Test cũ phải sửa vì thay đổi hợp lệ: `delivery/tests/test_confirmation_role_scope.py` (Group CSKH nay có thêm `view_callscript`), `ai/registry/tests/test_discipline.py` (số `@action` 29 → 30) và `ai/registry/tests/snapshots/commands_index_snapshot.json` (thêm `delivery.deliverynote.lookup`).

### 6. Lệch so với 02b và điều còn nợ
- Đường dẫn: 02b ghi `/api/cskh/scripts/`; code đã đổi tên sang `/api/confirmation/scripts/` (đợt đặt tên tiếng Anh). Nhóm `cskh` nay là `customer_service`, mã `delivery/cskh/` nay là `delivery/confirmation/`. Không có `accounts/00xx_grant_callscript` như 02b §2.7: thay bằng `delivery/0009` (theo yêu cầu điều phối).
- `lookup` tự động lọt vào registry lệnh AI (`delivery.deliverynote.lookup`, quyền `print_label`, chỉ đọc, không PII). Chưa chặn riêng. Nếu techlead muốn cấm AI gọi, thêm vào danh sách cấm của registry (việc của hồ sơ AI).
- Tình huống `RETURNING` do BE thêm theo choices của 02b §2.6; 02b §4.6 chưa nói rõ khách quen dùng kịch bản nào, nên đặt: khách có đơn khác đã xử lý thì `RETURNING`.
- Chưa có FE (CS-16/17/18) và chưa có dữ liệu mẫu kịch bản: bảng rỗng cho đến khi Chủ soạn.
- Chạy test trong worktree cần symlink `backend/staticfiles` từ checkout chính (test admin cần manifest tĩnh), và `DJANGO_DEBUG=1`. Symlink đã gỡ trước khi commit.

### 7. Kiểm chứng Lô 5 BE
- `makemigrations --check --dry-run`: **No changes detected**.
- `cd backend && python manage.py test`: **Ran 2883 tests, OK** (gồm 33 test mới).
- `python3 scripts/check_naming.py`: OK, không phát sinh vi phạm mới.
