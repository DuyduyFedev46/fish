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
