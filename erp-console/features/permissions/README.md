# features/permissions — Phân quyền

Story: **ED-40** (ma trận việc x nhóm, trang nhóm); ED-39 là phần BE (`/api/staff/groups/…`, đã có). Quyết định của Duy (#13):
quyền do admin cấu hình được; Chủ có thể bật "Xem khách hàng" cho nhóm bất kỳ, và khi bật thì màn **phải** ghi rõ "Tất cả khách".

Route: `/permissions/` (ma trận) và `/permissions/detail/?group=<mã nhóm>` (một nhóm). Bọc `<ViewGuard view="permissions">`
(cần `accounts.manage_staff`). Mọi người có quyền xem đều xem được; **Chủ hoặc superuser** thấy công tắc và ô chọn bấm được
(`isGroupWriter`; Duy chốt 06/10: FE mở cho superuser ngoài nhóm Chủ như BE). `/api/auth/me/` chưa trả `is_superuser`, nên
hàm nhận ra superuser qua việc có đủ quyền chỉ-Chủ; khi BE thêm cờ thì dùng cờ.

**Phạm vi dữ liệu cấu hình (PV-09, PV-10, PV-11, Lô F1):** W3i có khối "Phạm vi dữ liệu" 8 dòng (D1..D8 theo `data_scopes` của BE).
Việc và phạm vi là **bản nháp** trong bộ nhớ (`useGroupDraft`, `Draft` ở `permissionsModel`); thanh "Lưu thay đổi / Huỷ thay đổi"
gửi MỘT PUT có `version`. W3h (ma trận) vẫn bật/tắt ngay nhưng cũng gửi `version`.

## Contract BE (B4, R16: dưới `/api/staff/groups/`, khác chữ ở story)

| Hàm (`api.ts`) | Endpoint |
|---|---|
| `listGroups()` | `GET /api/staff/groups/` → nhóm kèm trạng thái từng việc |
| `getGroup(code)` | `GET /api/staff/groups/<code>/` → thành viên, registry các việc, phạm vi dữ liệu, dòng thời gian |
| `saveGroupChanges(code, {version, capabilities?, scopes?, confirm_customer_data_widening?})` | `PUT /api/staff/groups/<code>/capabilities/` → chi tiết nhóm mới (có `version` mới). 409 `GROUP_CHANGED`; 400 `CUSTOMER_DATA_WIDENING_UNCONFIRMED` kèm `impact` |
| `previewGroupChanges(code, {capabilities?, scopes?})` | `POST /api/staff/groups/<code>/permissions-preview/` → ai bị ảnh hưởng, không ghi gì (BE Lô 5) |

GET đã có `version`, `data_scope_values` (danh sách) và `data_scopes` 8 dòng (chi tiết) từ Lô 2. PUT mới và preview chỉ chạy ở bản mock
cho tới Lô 5 BE: **không deploy FE này trước Lô 5**.

Thêm / bỏ thành viên đi qua `PUT /api/staff/{id}/groups/` của module `staff` (một chỗ duy nhất đổi nhóm của một người).

## Luật FE

- Registry (danh sách việc, mục, khoá `requires`, "Chỉ Chủ") lấy từ `getGroup("owner")`, không gõ lại ở FE.
- Công tắc `role="switch"` tên `"<Việc> — <Nhóm>"`. Ở ma trận bật/tắt có hiệu lực ngay; chỉ **tắt việc phá luồng** (`view_orders`,
  `deliver`, `view_audit`) mới hỏi lại kèm số người bị ảnh hưởng (`breakingWarning`). Ở trang nhóm là bản nháp, câu hậu quả đó
  hiện một lần ở hộp xác nhận lúc bấm "Lưu thay đổi".
- Ô phạm vi mờ khi BE báo `inactive_reason` và việc gốc (`gate_capability`) chưa bật trong bản nháp; `gate_capability: null` thì chỉ
  dựa vào `inactive_reason`. Bật "Xem khách hàng" khi Khách hàng = Không xem: bản nháp (và W3h) tự đặt Khách hàng = Tất cả (PO-Q1).
- Lưu = xem trước (POST) → hộp xác nhận nếu mở rộng dữ liệu khách ("Tôi hiểu, lưu"), thu hẹp có dòng bị ảnh hưởng, hoặc tắt việc phá
  luồng → PUT. Xem trước hỏng mạng thì bỏ qua (BE vẫn chặn ở PUT, rồi FE mở hộp bằng `impact`).
- Chip "Được gán" lấy từ `data_scope_values` (không còn hằng số theo nhóm).
- Việc có `requires`: bật/tắt đi cùng yêu cầu với việc gốc (`planToggle`), tất cả hoặc không gì cả.
- Cột nhóm Chủ cố định (không có công tắc). Việc "Chỉ Chủ" của nhóm khác khoá, không có công tắc (BR-PQ-32).
- "Xem khách hàng" đang bật ở nhóm khác Chủ: nhãn "Tất cả khách" hiện ngay trong ô (`ALL_CUSTOMERS_LABEL`).
- Lỗi BE hiện nguyên văn `detail`. Không cập nhật "lạc quan": ô chỉ đổi khi BE đã nhận, nên không bao giờ hiện quyền chưa lưu.
- Mock (`mock.ts` + phần thuần `mockScopes.ts`) giữ đủ luật BE theo thứ tự kiểm 02b §2.3: chỉ Chủ/superuser ghi, nhóm Chủ khoá,
  không cấp việc "Chỉ Chủ", `CAPABILITY_REQUIRES`, CAS `version` (409 `GROUP_CHANGED`), PO-Q1, mở rộng dữ liệu khách thiếu xác nhận
  → 400 kèm `impact`, không đổi gì thì không tăng `version`. Thay đổi giữ trong `sessionStorage` (`cave_erp_mock_group_caps`,
  `_scopes`, `_versions`, `_events`: chỉ khoá việc, mã đối tượng, mã giá trị, số phiên bản, tên đăng nhập người sửa) và **không** làm
  đổi quyền lúc đăng nhập mock. Số "dòng mất quyền xem" của bản xem trước là số giả (3 phiếu nhập, 2 loại khác). Thử 409:
  `window.__caveMock.bumpGroupVersion("manager")`. Thành viên lấy từ kho người dùng mock của `features/auth`.

## File

| File | Làm gì |
|---|---|
| `api.ts` · `mock.ts` · `types.ts` · `messages.ts` | API (kèm mock), kiểu, chữ UI một chỗ |
| `permissionsModel.ts` (+ test) | hàm thuần: chia mục, `cellMode`, `planToggle`, cảnh báo phá luồng, tìm bỏ dấu, `groupHref`, đọc `?group=`, `isGroupWriter`, bản nháp (`toggleInDraft`, `setScopeInDraft`, `cleanDraft`, `saveBodyOf`), ô mờ (`isScopeInactive`) |
| `mockScopes.ts` · `mock.test.ts` | danh mục D1..D8 chép từ BE, dựng `data_scopes`, đánh giá mở rộng dữ liệu khách, bản xem trước; test luật mock |
| `useGroupDraft.ts` · `saveErrors.ts` | bản nháp + luồng lưu của W3i (xem trước, xác nhận, 409); đọc lỗi PUT |
| `components/ConfirmSaveModal.tsx` | hộp xác nhận lưu: cảnh báo mở rộng dữ liệu khách, ghi chú thu hẹp, câu hậu quả |
| `useCapabilityToggle.ts` | bật/tắt dùng chung ma trận và trang nhóm (hỏi lại khi cần, khoá ô đang gửi, đổi ô khi BE đã nhận) |
| `useGroupData.ts` | tải danh sách nhóm / một nhóm (dùng bộ tải của `features/staff/useLoaded.ts`) |
| `components/PermissionMatrixScreen.tsx` | ma trận, tìm việc, cột nhóm có link tới trang nhóm |
| `components/GroupDetailScreen.tsx` | trang nhóm: việc được làm, phạm vi dữ liệu, thành viên, dòng thời gian |
| `components/PermSwitch.tsx` · `ConfirmOffModal.tsx` · `AddMemberModal.tsx` · `RemoveMemberModal.tsx` | công tắc, hộp hỏi lại, thêm / gỡ thành viên |
| `permissions.module.css` | kiểu của module (chỉ token) |

Kịch bản: `e2e/ed_batch14_permissions.py` (mock, kèm 403, ngoài đường thuận, mobile 360).
