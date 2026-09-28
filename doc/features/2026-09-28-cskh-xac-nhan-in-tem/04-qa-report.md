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
