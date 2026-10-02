# features/staff — Nhân sự

Story: **ED-37** (danh sách, hồ sơ, thêm nhân viên, tạo tài khoản Chủ), **ED-38** (sửa hồ sơ, đổi nhóm, đặt lại mật khẩu,
cho nghỉ / làm lại), nền là S41, S42, S48 của BE L5/L6b. Lô 14 (ERP theo design) thay bản SideSheet cũ.

Route: `/staff/` (danh sách) và `/staff/detail/?id=<số>` (hồ sơ). Cả hai bọc `<ViewGuard view="staff">`: cần
`accounts.manage_staff`, người khác thấy "Bạn không có quyền xem mục này" và **không** có request nào tới `/api/staff`.
Phân quyền nhóm (ma trận) nằm ở `features/permissions`.

## Contract BE (thực tế, L5)

| Hàm (`api.ts`) | Endpoint |
|---|---|
| `listStaff(filter)` | `GET /api/staff/` (bỏ `is_active` = tất cả) → mảng, không phân trang |
| `getStaff(id)` | `GET /api/staff/{id}/` |
| `createStaff(input)` | `POST /api/staff/` → 201 |
| `updateStaff(id, {display_name, phone})` | `PATCH /api/staff/{id}/` |
| `setStaffGroups(id, groups)` | `PUT /api/staff/{id}/groups/` → `{groups, added, removed}` |
| `deactivateStaff(id)` / `reactivateStaff(id)` | `POST /api/staff/{id}/deactivate/` · `/reactivate/` |
| `resetStaffPassword(id, pw)` | `POST /api/staff/{id}/reset-password/` → `{}` |
| `getStaffTimeline(id)` | `GET /api/guidance/staff/{id}/` (chỉ dùng `timeline`) |
| `fetchStaffActivity(id)` | `GET /api/audit-logs/?actor={id}` (chỉ khi có quyền xem nhật ký) |
| `fetchStaffDelivering(id)` | `GET /api/delivery/notes/?assigned_to={id}&status=DELIVERING` (bỏ hết trường về khách) |

## Luật FE

- Nút thao tác **chỉ** hiện theo `available_actions` của từng người (BE tính cả luật lẫn quyền). Thao tác không làm được
  vẫn hiện trong menu "…" nhưng mờ kèm lý do (`blockedReason` trong `staffModel.ts`), không ẩn.
- Lỗi BE hiện **nguyên văn** `detail` ở đầu hộp (BR-PQ-08/17/18, BR-GH-08, BR-PQ-01). Biểu mẫu dùng `noValidate`.
- Hộp "Cho nghỉ" nêu sẵn số phiếu Đang giao kèm mã phiếu và khoá nút xác nhận khi còn từ 1 phiếu (ED-38-AC3, BR-GH-08, `deliveringBlock`).
  Khối "Việc đang giao" không tải được (thiếu quyền xem phiếu, lỗi) thì không khoá, để BE quyết khi bấm xác nhận.
- Hỏi lại trước khi: cho nghỉ; thêm hoặc bỏ nhóm Chủ (đổi nhóm và tạo tài khoản có nhóm Chủ).
- Không có nháp biểu mẫu: tên, SĐT, mật khẩu chỉ ở state của hộp, không vào `localStorage`, URL, log. Số điện thoại hiện đủ
  trong màn quản trị này (người dùng đã có `manage_staff`), không bao giờ đưa vào URL.
- Mật khẩu tạm (S48): ô chung + "Nhập lại"; lệch hoặc trống → báo tại ô, KHÔNG gọi API. "Tạo ngẫu nhiên" điền cả hai ô.
- Tab Đang làm / Đã nghỉ / Tất cả tính phía máy từ MỘT lần `listStaff("all")` (`useStaffData.ts`); tab nằm trên URL (`?tab=`).
- Mock (`mock.ts`) mô phỏng bảng lỗi và `available_actions` của BE, dùng chung kho người dùng mock của `features/auth`.
  Seed: `giao2` còn 2 phiếu Đang giao (BR-GH-08), `ql9` có `manage_staff` nhưng không thuộc Chủ (BR-PQ-17), `sa1` là
  superuser + Quản lý (BR-PQ-18), `nghi1` đã nghỉ. Mật khẩu demo chỉ ở kho mock, không ở file khác.

## File

| File | Làm gì |
|---|---|
| `api.ts` · `mock.ts` · `types.ts` · `messages.ts` | hàm API (kèm nhánh mock), mock một handler, kiểu, chữ UI một chỗ |
| `staffModel.ts` (+ test) | hàm thuần: đếm/lọc tab, `can`, `blockedReason`, so sánh nhóm, nhãn hoạt động, đọc `?id=` |
| `useLoaded.ts` · `useStaffData.ts` | bộ tải dùng chung (tải/lỗi/403/không thấy, Thử lại) · danh sách, hồ sơ, dòng thời gian, hoạt động, phiếu đang giao |
| `components/StaffScreen.tsx` | danh sách DataTable + tab + tìm + khối "Nhóm quyền" (nếu có quyền xem) |
| `components/StaffDetailScreen.tsx` | hồ sơ: header (Sửa hồ sơ, Đổi nhóm, "…"), thông tin, quyền theo nhóm, việc đang giao, hoạt động, dòng thời gian |
| `components/StaffFormModal.tsx` | Thêm nhân viên: biểu mẫu → (nhóm Chủ thì hỏi lại) → "Đã tạo" kèm mật khẩu tạm |
| `components/EditProfileModal.tsx` · `GroupsModal.tsx` · `ResetPasswordModal.tsx` · `ActiveModal.tsx` | các thao tác trên hồ sơ |
| `components/GroupPicker.tsx` · `PasswordField.tsx` · `CopyButton.tsx` · `parts.tsx` | ô chọn nhóm, cặp ô mật khẩu, nút chép, phần nhỏ dùng chung |
| `staff.module.css` | kiểu của module (chỉ token) |

Móc e2e: `main tr.lt-click`, `td[data-label="Tên đăng nhập"]`, `.group-tag`, `.cred-username`, `.cred-password`,
`role=dialog`, `.toast-item`. Kịch bản: `e2e/ed_batch14_permissions.py`, `s41_s47_staff.py`, `s48_password.py`,
`s41_s47_real.py` (BE thật).
