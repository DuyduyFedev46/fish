# Báo cáo QA — Tính năng CSKH: Xác nhận đơn & In tem

Hồ sơ: `doc/features/2026-09-28-cskh-xac-nhan-in-tem/`
Quy trình: Kiểm thử độc lập theo TDD, kiểm tra ma trận phân quyền, bất biến giá vốn & PII, kiểm tra hồi quy.

---

## Lô 1 — Nền: Group `cskh`, phạm vi dữ liệu cá nhân, bảng + chi tiết phiếu giao (CS-01, CS-02, CS-03)

- Ngày kiểm thử: 2026-09-29
- Người thực hiện: QA Tester (`qa-tester` subagent)
- Kết luận: **APPROVED**
- Tổng số ca kiểm thử: 28 · ✅ 28 · ❌ 0 · ⏸ 0

### 1. Bảng kết quả theo Acceptance Criteria

| Mã AC | Tiêu chí | Kết quả | Bằng chứng (test / code audit) |
|---|---|:---:|---|
| **CS-01-AC1** | Migration Group `cskh` + 4 quyền, idempotent khi chạy lại | ✅ PASS | `test_cskh_l1.py::test_cs01_ac1_group_cskh_permissions_and_idempotent_migration`, migration `0011_seed_group_cskh.py` có hàm `grant`/`revoke` an toàn. |
| **CS-01-AC2** | `cs1` gọi `/api/auth/me/` -> home="cskh-queue", can_view_cost=False, nhãn CSKH | ✅ PASS | `test_cskh_l1.py::test_cs01_ac2_me_endpoint_for_cskh`, `describe_user` trong `accounts/auth/services.py`. |
| **CS-01-AC3** | `cs1` xem danh sách đơn: thấy D1 (PENDING), D2 (ESCALATED), D4 (đã gọi 2 ngày); không thấy D3 (READY) | ✅ PASS | `test_cskh_l1.py::test_cs01_ac3_cskh_order_scope_filtering`, `SalesOrderViewSet.get_queryset` lọc qua `Exists` + `cskh_note_q`. |
| **CS-01-AC4** | Xem đơn D3 ngoài phạm vi -> 404; xem `/api/sales/customers/{id}/` -> 403 | ✅ PASS | `test_cskh_l1.py::test_cs01_ac4_cskh_out_of_scope_404_and_customer_403`, `cskh` không có `sales.view_customer`. |
| **CS-01-AC5** | Gọi cách đây 8 ngày: mặc định (7 ngày) -> 404; `CSKH_PII_RECENT_DAYS=10` -> 200 | ✅ PASS | `test_cskh_l1.py::test_cs01_ac5_cskh_pii_recent_days`, `override_settings(CSKH_PII_RECENT_DAYS=10)`. |
| **CS-01-AC6** | `cs2` gọi hôm qua, `cs1` xem đơn đó -> 404 (phạm vi tính theo từng nhân viên) | ✅ PASS | `test_cskh_l1.py::test_cs01_ac6_cskh_scope_by_user`. |
| **CS-01-AC7** | `cs1` gọi các endpoint điều phối delivery (GET /api/delivery/notes/, POST status) -> 403 | ✅ PASS | `test_cskh_l1.py::test_cs01_ac7_cskh_matrix_403`. |
| **CS-01-AC8** | Quản lý gán Group `cskh` -> 403; chỉ Chủ có `manage_staff` gán được, có AuditLog | ✅ PASS | `StaffViewSet` chặn bằng `manage_staff`, `apps.accounts` suite bảo vệ. |
| **CS-02-AC1** | Nhóm 6 tab trạng thái hoạt động (không có CANCELLED); Hoàn tất lọc hôm nay | ✅ PASS | `test_cskh_l1.py::test_cs02_ac1_deliveries_grouped_by_status`, FE `deliveries.test.ts`, `STATUS_GROUP_TABS`. |
| **CS-02-AC2** | Phiếu PREPARING chưa in tem có nhãn "Chưa in tem"; xếp `confirmed_at` cũ/null lên đầu | ✅ PASS | `test_cskh_l1.py::test_cs02_ac2_deliveries_ordering_and_unprinted_label`, `F("confirmed_at").asc(nulls_first=True)`. |
| **CS-02-AC3** | Phiếu CONFIRMING có `available_actions = []`, không nút thao tác | ✅ PASS | `test_cskh_l1.py::test_cs02_ac3_confirming_available_actions_empty`, `DeliveryNoteSerializer.get_available_actions`. |
| **CS-02-AC4** | `giao1` chỉ thấy phiếu gán cho mình; menu Giao hàng điều phối ẩn với `onlyDelivery` | ✅ PASS | `test_cskh_l1.py::test_cs02_ac4_giao_only_sees_assigned_notes`, `nav.ts:onlyDelivery(me)`. |
| **CS-02-AC5** | `cs1` chỉ thuộc `cskh`: GET /api/delivery/notes/ -> 403; menu không hiện | ✅ PASS | `test_cskh_l1.py::test_cs01_ac7_cskh_matrix_403`, `nav.ts` kiểm tra `PERM.viewDeliveryNote`. |
| **CS-02-AC6** | Mobile 360×640: dạng thẻ `.cardItem`, không cuộn ngang, vùng bấm thẻ ≥ 44px | ✅ PASS | `deliveries.module.css: @media (max-width: 768px)`, `.tableWrapper` ẩn, `.cardsContainer` dạng cột. |
| **CS-02-AC7** | Bảng phiếu giao không lộ bất kỳ key giá vốn nào; không lộ giá bán từng dòng | ✅ PASS | `test_cskh_l1.py::test_cs02_ac7_no_cost_leak_in_delivery_notes`, `deliveries.test.ts`. |
| **CS-03-AC1** | Chi tiết phiếu PREPARING có dòng hàng theo lô FEFO đã chốt và HSD | ✅ PASS | `test_cskh_l1.py::test_cs03_ac1_detail_lines_with_expiry`, `DeliveryDetailModal.tsx`. |
| **CS-03-AC2** | Bấm "Đã đóng gói" (to_status=READY) -> trạng thái READY, 1 AuditLog | ✅ PASS | `test_cskh_l1.py::test_cs03_ac2_pack_delivery_note_advance_to_ready`. |
| **CS-03-AC3** | Mạng rớt / bấm đúp gửi lại `from_status=PREPARING` -> 200 `already: true`, không thêm AuditLog | ✅ PASS | `test_cskh_l1.py::test_cs03_ac3_advance_status_idempotent_already_true`, `advance_status`. |
| **CS-03-AC4** | Phiếu PREPARING -> COMPLETED -> 400 `BR-GH-05` | ✅ PASS | `test_cskh_l1.py::test_cs03_ac4_invalid_transition_returns_400_br_gh_05`. |
| **CS-03-AC5** | Phiếu CANCELLED -> bất kỳ trạng thái -> 400 `BR-GH-07` ("Đơn đã huỷ, không soạn") | ✅ PASS | `test_cskh_l1.py::test_cs03_ac5_cancelled_note_returns_400_br_gh_07`. |
| **CS-03-AC6** | `giao1` được gán phiếu PREPARING gọi PREPARING -> READY -> 403 (thiếu `pack_deliverynote`) | ✅ PASS | `test_cskh_l1.py::test_cs03_ac6_giao_cannot_pack_403`. |
| **CS-03-AC7** | `cs1` gọi `GET /api/delivery/notes/31/` -> 403 | ✅ PASS | `BusinessModelPermissions` chặn vì `cskh` thiếu `view_deliverynote`. |
| **CS-03-AC8** | Chi tiết phiếu giao cho NV kho không có key giá vốn hay đơn giá mua | ✅ PASS | `test_cskh_l1.py::test_cs02_ac7_no_cost_leak_in_delivery_notes`, `DeliveryNoteDetailSerializer`. |

---

### 2. Kiểm tra Bất biến & Ngoại lệ chuẩn (X-AC)

1. **Bất biến 1 — Không rò giá vốn (X-AC3):**
   - Quét grep đệ quy: Không có `unit_cost`, `purchase_rate`, `landed_unit_cost`, `margin`, `profit` trong `DeliveryNoteSerializer`, `DeliveryNoteDetailSerializer`, hay `features/deliveries/types.ts`.
   - Kết quả test: Token mọi Group (`chu`, `quan_ly`, `nv_kho`, `nv_giao`, `cskh`) đều không thấy key giá vốn trên endpoint phiếu giao.
   - Trạng thái: ✅ **ĐẠT**

2. **Bất biến 9 — Không rò dữ liệu cá nhân khách (X-AC1, X-AC4):**
   - Bảng điều phối phiếu giao không trả SĐT khách (`phone`, `recipient_phone`).
   - `DeliveryNoteAdmin`: `exclude = ("recipient_name", "recipient_phone")` ngăn rò PII vào AuditLog khi admin lưu.
   - `ConfirmationTask.__str__` chỉ hiển thị mã `f"Chờ gọi {self.note_id}"`.
   - Frontend không lưu PII vào `localStorage`, `sessionStorage`, URL hay `console.*`.
   - Trạng thái: ✅ **ĐẠT**

3. **Bất biến 3 — Không xoá chứng từ (X-AC6):**
   - `DeliveryNoteViewSet` kế thừa `DocumentViewSet`, không có action DELETE (HTTP 405).
   - Toàn bộ các trường trạng thái, thông tin xác nhận và thông tin người nhận hộ nằm trong `locked_fields` -> Gọi PATCH/PUT trực tiếp bị chặn 400 `BR-PQ-14`.
   - `ConfirmationTask`, `CustomerCall`, `LabelPrint` có `default_permissions = ()`, không mở API xoá.
   - Trạng thái: ✅ **ĐẠT**

4. **Ma trận phân quyền Tầng 1 / Tầng 2 / Tầng 3 (X-AC7):**
   - `GET /api/delivery/notes/`: chu (200), quan_ly (200), nv_kho (200), nv_giao (200, chỉ phiếu của mình), cskh (403), không Group (403).
   - `POST /api/delivery/notes/{id}/status/` -> READY: chu (200), quan_ly (200), nv_kho (200), nv_giao (403), cskh (403), không Group (403).
   - `GET /api/sales/orders/`: chu (200), quan_ly (200), nv_kho (200), nv_giao (chỉ đơn của mình), cskh (chỉ đơn trong phạm vi BR-GH-18), không Group (403).
   - Trạng thái: ✅ **ĐẠT**

---

### 3. Kết quả kiểm chứng hồi quy

- Backend: **824/824 tests xanh 100%**.
- `erp-console`: **21/21 vitest tests xanh 100%**.
- Build tĩnh `erp-console`: 25/25 static pages sạch (cả bản tiêu chuẩn lẫn bản MOCK).
- Build tĩnh `frontend` (Shop): 8/8 static pages sạch.
- Schema & Migrations: `makemigrations --check --dry-run` không có thay đổi chưa migrate; migrate idempotent.
- Lỗi phát hiện: **0 lỗi** (0 Critical, 0 High, 0 Medium, 0 Low).

---

### 4. Kết luận
**APPROVED — Lô 1 sẵn sàng commit và push.**

---

## Lô 2 — Luồng xác nhận chạy được sớm nhất (gọi → xác nhận → in tem tay → soạn)

- Ngày kiểm thử: 2026-09-29
- Người thực hiện: QA Tester (`qa-tester` subagent)
- Kết luận: **APPROVED**
- Tổng số ca kiểm thử: 43 · ✅ 43 · ❌ 0 · ⏸ 0

### 1. Bảng kết quả theo Acceptance Criteria

| Mã AC | Tiêu chí | Kết quả | Bằng chứng (test / code audit) |
|---|---|:---:|---|
| **CS-04-AC1** | IPN thanh toán đủ tiền -> đơn PROCESSING, hoá đơn ISSUED, note CONFIRMING, task PENDING | ✅ PASS | `test_cskh_l2.py::test_cs04_ac1_signal_creates_note_confirming_and_task_pending`, signal `post_save` trong `delivery/signals.py`. |
| **CS-04-AC2** | Xác nhận tay (S11) và hàng chờ lệch (S12) -> phiếu đều CONFIRMING | ✅ PASS | Đều qua `issue_invoice` -> signal tạo CONFIRMING; suite `test_s11_confirm_manual.py`, `test_s12_payment_queue.py`. |
| **CS-04-AC3** | IPN gửi lại lần 2 -> idempotent, đúng 1 note, 1 task | ✅ PASS | `test_cskh_l2.py::test_cs04_ac3_idempotent_ipn_does_not_duplicate`, `start_confirmation` dùng `select_for_update` + `get_or_create`. |
| **CS-04-AC4** | Phiếu CONFIRMING gọi POST .../status chuyển PREPARING/READY -> 400 `BR-GH-11` | ✅ PASS | `apps/delivery/services.py:advance_status` chặn 400 `BR-GH-11`, `ALLOWED_TRANSITIONS[CONFIRMING] = set()`. |
| **CS-04-AC5** | Quản lý huỷ đơn khi CONFIRMING -> hoàn kho đúng lô gốc (CANCEL_RESTORE), task DONE | ✅ PASS | `test_cskh_l2.py::test_cs04_ac5_cancel_paid_order_when_confirming_restores_stock`, `_STOCK_STILL_IN_WAREHOUSE` có CONFIRMING. |
| **CS-04-AC6** | Phiếu CONFIRMING 3 ngày -> bảng phân bổ lô giữ nguyên (không re-allocate) | ✅ PASS | `SalesInvoiceLineBatch` đóng băng từ lúc ISSUED (BR-BH-11). |
| **CS-04-AC7** | Chạy migration không làm đổi trạng thái phiếu cũ sang CONFIRMING | ✅ PASS | Migration `0004_cskh_confirmation` chỉ thêm field và choices, default giữ PREPARING. |
| **CS-04-AC8** | `giao1` gọi GET /api/delivery/notes/ không thấy phiếu CONFIRMING chưa gán | ✅ PASS | `DeliveryNoteViewSet.get_queryset` lọc `assigned_to=giao1` cho NV giao. |
| **CS-05-AC1** | Hàng chờ CSKH mặc định lọc PENDING + CALLBACK hợp lệ, sắp xếp theo `paid_at` tăng dần | ✅ PASS | `test_cskh_l2.py::test_cs05_ac1_queue_list_default_and_ordering`, FE `cskh.test.ts`. |
| **CS-05-AC2** | Phiếu CALLBACK hẹn 10:00 -> 09:50 không thấy ở mặc định, 10:00 thấy; lọc ?state=CALLBACK thấy lúc 09:50 | ✅ PASS | `CskhQueueViewSet.list` lọc `Q(state=PENDING) \| (Q(state=CALLBACK) & Q(callback_at__lte=now))`. |
| **CS-05-AC3** | Khoá mềm claim đơn trong 5 phút, người khác gọi claim/calls -> 409 `CLAIMED` | ✅ PASS | `test_cskh_l2.py::test_cs05_ac3_ac4_claim_task_soft_lock_and_expiry`, `cskh.test.ts`. |
| **CS-05-AC4** | Qua `CSKH_CLAIM_MINUTES` -> người khác claim được thành công | ✅ PASS | `test_cskh_l2.py::test_cs05_ac3_ac4_claim_task_soft_lock_and_expiry`. |
| **CS-05-AC5** | Tìm kiếm SĐT trả đủ thông tin cho đơn trong scope, che PII cho đơn ngoài scope | ✅ PASS | `test_cskh_l2.py::test_cs05_ac5_in_scope_and_pii_masking`, `cskh.test.ts`. |
| **CS-05-AC6** | Search chỉ nhận POST (GET 405), tìm đúng SĐT hoặc mã đơn, gõ < 9 số -> 400 `INVALID_QUERY`, throttle 429 | ✅ PASS | `test_cskh_l2.py::test_cs05_ac6_search_endpoint`, `test_cs05_search_throttling`. |
| **CS-05-AC7** | Đơn CANCELLED rời hàng chờ; tải lại chi tiết báo đơn đã huỷ, mất nút kết quả | ✅ PASS | `close_task_on_cancel` đưa task về DONE; `claim_task`/`record_call` trả 400 `BR-GH-07`. |
| **CS-05-AC8** | Mobile 360×640: link `tel:`, nút kết quả cao ≥ 44px ở nửa dưới màn hình, không cuộn ngang | ✅ PASS | `CskhCallModal.tsx`: `<a href="tel:...">`, `cskh.module.css`: `.callNowBtn` 48px, `.resultBtn` 52px. |
| **CS-05-AC9** | `kho1`, `giao1` gọi GET /api/cskh/queue/ -> 403; menu Gọi xác nhận ẩn | ✅ PASS | `test_cskh_l2.py::test_cs05_headers_and_permissions`, `nav.ts` kiểm `PERM.confirmWithCustomer`. |
| **CS-06-AC1** | Ghi CONFIRMED -> note sang PREPARING, confirmed_at/by, 1 AuditLog `delivery_confirmed` | ✅ PASS | `test_cskh_l2.py::test_cs06_ac1_ac2_confirmed_advances_to_preparing_and_idempotent`, `cskh.test.ts`. |
| **CS-06-AC2** | Gửi lại cùng request_id -> 200 `duplicate=True`, không sinh thêm bản ghi gọi hay AuditLog | ✅ PASS | `test_cskh_l2.py::test_cs06_ac1_ac2_confirmed_advances_to_preparing_and_idempotent`. |
| **CS-06-AC3** | Xung đột xác nhận khi đơn đã xử lý -> 409 `STALE_STATE` | ✅ PASS | `record_call` kiểm tra `task.state in open_states`, trả `ConflictError(code="STALE_STATE")`. |
| **CS-06-AC4** | Ghi CALLBACK hẹn giờ tương lai -> confirm_state=CALLBACK, attempts không tăng | ✅ PASS | `test_cskh_l2.py::test_cs06_ac3_callback_schedule`, `cskh.test.ts`. |
| **CS-06-AC5** | Ghi CALLBACK với callback_at ở quá khứ hoặc thiếu -> 400 `INVALID_INPUT` | ✅ PASS | `test_cskh_l2.py::test_cs06_ac3_callback_schedule`. |
| **CS-06-AC6** | Ghi chú cuộc gọi chứa SĐT hoặc STK (≥ 9 chữ số liên tiếp) hoặc > 200 ký tự -> 400 `BR-GH-19` | ✅ PASS | `test_cskh_l2.py::test_cs06_ac6_pii_blocking_br_gh_19`, `cskh.test.ts`. |
| **CS-06-AC7** | Đơn CANCELLED ghi bất kỳ kết quả gọi nào -> 400 `BR-GH-07` | ✅ PASS | `record_call` kiểm tra `note.status == DeliveryNote.Status.CANCELLED`. |
| **CS-06-AC8** | Huỷ xác nhận PREPARING -> CONFIRMING khi chưa in tem; chặn 400 `BR-GH-16` khi tem đã in | ✅ PASS | `test_cskh_l2.py::test_cs06_ac8_unconfirm_and_blocked_if_label_printed`, `cskh.test.ts`. |
| **CS-06-AC9** | Lịch sử cuộc gọi hiển thị mới nhất trước, có giờ, nhãn kết quả tiếng Việt, người gọi, ghi chú | ✅ PASS | `CskhQueueDetailSerializer` sắp xếp `-created_at, -id`, `CustomerCallSerializer`. |
| **CS-06-AC10** | Phân quyền ghi cuộc gọi: `kho1` 403; `cs1` ngoài phạm vi 404 | ✅ PASS | `CskhQueueViewSet.calls` kiểm `confirm_with_customer` (403) và `note_in_cskh_scope` (404). |
| **CS-11-AC1** | Phiếu PREPARING in tem -> print_no=1, 1 AuditLog `label_printed`, hộp thoại in mở | ✅ PASS | `test_cskh_l2.py::test_cs11_ac2_record_print_and_idempotent`, `cskh.test.ts`, `DeliveryDetailModal.tsx`. |
| **CS-11-AC2** | Phiếu CONFIRMING không in được tem -> 400 `BR-GH-09`; FE ẩn nút In tem | ✅ PASS | `test_cskh_l2.py::test_cs11_ac3_cannot_print_if_confirming_or_cancelled`, `cskh.test.ts`. |
| **CS-11-AC3** | Phiếu CANCELLED không in được tem -> 400 `BR-GH-07` | ✅ PASS | `test_cskh_l2.py::test_cs11_ac3_cannot_print_if_confirming_or_cancelled`. |
| **CS-11-AC4** | Dữ liệu tem và DOM trang in tuyệt đối không chứa giá bán, tổng tiền hay giá vốn | ✅ PASS | `test_cskh_l2.py::test_cs11_ac1_preview_label_data_no_cost_no_amount`, `cskh.test.ts`. |
| **CS-11-AC5** | SĐT trên tem chỉ ở dạng che mask (09xx xxx 123) | ✅ PASS | `test_cskh_l2.py::test_cs11_ac1_preview_label_data_no_cost_no_amount`, `cskh.test.ts`. |
| **CS-11-AC6** | Khổ in 100×150 mm (CSS @page), địa chỉ dài tự cắt tối đa 4 dòng có dấu "..." | ✅ PASS | `erp-console/app/print/label/page.tsx`: `<style>@page { size: 100mm 150mm; margin: 0; }</style>`. |
| **CS-11-AC7** | QR code SVG sinh client chứa đúng barcode_value (`GH-....1`), không URL, không SĐT | ✅ PASS | `QRCode.toString(data.barcode_value, {type: "svg", ...})`. |
| **CS-11-AC8** | In tem idempotent theo `request_id` -> 200 `duplicate=True`, vẫn print_no=1 | ✅ PASS | `test_cskh_l2.py::test_cs11_ac2_record_print_and_idempotent`. |
| **CS-11-AC9** | `cs1`, `giao1` gọi GET label hoặc POST print -> 403 | ✅ PASS | `test_cskh_l2.py::test_cs11_permissions_and_cache_control`. |

### 2. Kiểm tra Bất biến & Ngoại lệ chuẩn (X-AC)

1. **Bất biến 1 — Không rò giá vốn (X-AC3):**
   - Quét mã nguồn serializers (`CskhQueueItemSerializer`, `CskhQueueDetailSerializer`, `get_label_data`): không chứa các key `unit_cost`, `purchase_rate`, `landed_unit_cost`, `cost`, `margin`, `profit`.
   - Test tự động đã kiểm tra token các Group (`chu`, `quan_ly`, `cskh`, `nv_kho`) trên các endpoint Lô 2.
   - Kết quả: ✅ **ĐẠT**.

2. **Bất biến 9 — Không rò dữ liệu cá nhân khách (X-AC1, X-AC2, X-AC4):**
   - **X-AC1 (Log)**: Không logger nào ghi nhận tên/SĐT/địa chỉ hay ghi chú tự do.
   - **X-AC4 (FE Storage / URL / Console)**: Quét grep `localStorage`, `sessionStorage`, `useDraft`, `console.*` trên `features/cskh`, `features/deliveries`, `app/print` -> **Rỗng 100%**. Không có import `features/ai`.
   - **X-AC2 (AuditLog)**: Đã kiểm tra lại lỗi B1 sau khi sửa: `AuditLog.changes` chỉ ghi `{"fields": ["recipient_name", "recipient_phone"]}`, hoàn toàn không chứa chuỗi SĐT hoặc tên khách.
   - Kết quả: ✅ **ĐẠT**.

3. **Bất biến 3 — Không xoá chứng từ (X-AC6):**
   - `CustomerCall`, `LabelPrint` không có endpoint sửa/xoá (append-only).
   - `DeliveryNote` các trường mới nằm trong `locked_fields`.
   - Kết quả: ✅ **ĐẠT**.

4. **Ma trận quyền (X-AC7) cho endpoint Lô 2:**
   - `GET /api/cskh/queue/`: chu (200), quan_ly (200), nv_kho (403), nv_giao (403), cskh (200), không Group (403).
   - `POST /api/cskh/search/`: chu (200), quan_ly (200), nv_kho (403), nv_giao (403), cskh (200), không Group (403).
   - `GET /api/delivery/notes/{id}/label/`: chu (200), quan_ly (200), nv_kho (200), nv_giao (403), cskh (403), không Group (403).
   - `POST /api/delivery/notes/{id}/label/print/`: chu (200), quan_ly (200), nv_kho (200), nv_giao (403), cskh (403), không Group (403).
   - Kết quả: ✅ **ĐẠT**.

5. **Header Cache-Control: no-store:**
   - Cả `CskhQueueViewSet`, `CskhSearchView`, `DeliveryNoteViewSet` đều gắn mixin `NoStoreMixin`. Test xác nhận header `Cache-Control: no-store` hiện diện.
   - Kết quả: ✅ **ĐẠT**.

### 3. Xác nhận xử lý lỗi

- **B1 (Critical - rò PII vào AuditLog)**: ĐÃ KHẮC PHỤC TRIỆT ĐỂ.
  - `backend/apps/delivery/cskh/services.py:427-438` đã cập nhật ghi `changes={"fields": changed_fields}` (chỉ lưu tên trường thay đổi, không lưu giá trị).
  - `test_cs06_change_recipient` trong `backend/apps/delivery/tests/test_cskh_l2.py` đã assert trực tiếp:
    - `self.assertEqual(audit.changes, {"fields": ["recipient_name", "recipient_phone"]})`
    - `self.assertNotIn("0988776655", str(audit.changes))`
    - `self.assertNotIn("Anh Ba Nhận Hộ", str(audit.changes))`

### 4. Kết quả kiểm chứng hồi quy

1. `cd backend && .venv/bin/python manage.py test apps.delivery`: **56/56 tests xanh 100%**.
2. `cd backend && .venv/bin/python manage.py test`: **843/843 tests xanh 100%**.
3. `cd backend && .venv/bin/python manage.py makemigrations --check --dry-run`: `No changes detected`.
4. `cd erp-console && npm test`: **4 test files, 35/35 tests xanh 100%**.
5. `cd erp-console && npx tsc --noEmit && npm run build`: 27/27 static pages pass 100%.
6. `cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build`: 27/27 static pages pass 100%.
7. `cd frontend && npx tsc --noEmit && npm run build`: 8/8 static pages pass 100%.
8. `grep -rn "localStorage\|sessionStorage\|useDraft\|console\." erp-console/features/cskh erp-console/features/deliveries erp-console/app/print`: **Rỗng 100%**.
9. `grep -rn "features/ai" erp-console/features/cskh erp-console/features/deliveries erp-console/app/print`: **Rỗng 100%**.

### 5. Kết luận
**APPROVED — Lô 2 đạt toàn bộ tiêu chuẩn chất lượng, sẵn sàng commit và push.**
