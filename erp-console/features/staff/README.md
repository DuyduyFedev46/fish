# features/staff — Nhân viên & phân quyền

Story: **S41** (tạo tài khoản, gán nhiều nhóm, sửa hồ sơ, đổi nhóm) và **S42** (cho nghỉ / cho làm lại, đặt lại
mật khẩu). Route `/staff/`, menu "Nhân sự · Nhật ký". Quyền xem màn: `accounts.manage_staff` (seed chỉ `chu` có).

Contract **thực tế** BE L5 (03-dev-notes.md "Lô L5 — S41, S42"):

| Hàm (`api.ts`) | Endpoint |
|---|---|
| `listStaff(filter)` | `GET /api/staff/?is_active=true\|false` (bỏ tham số = tất cả) → mảng, không phân trang |
| `createStaff(input)` | `POST /api/staff/` → 201 một dòng đầy đủ |
| `updateStaff(id, {display_name, phone})` | `PATCH /api/staff/{id}/` |
| `setStaffGroups(id, groups)` | `PUT /api/staff/{id}/groups/` → `{groups, added, removed}` |
| `deactivateStaff(id)` / `reactivateStaff(id)` | `POST /api/staff/{id}/deactivate/` · `/reactivate/` |
| `resetStaffPassword(id, pw)` | `POST /api/staff/{id}/reset-password/` → `{}` |

Luật FE:
- Nút thao tác **chỉ** hiện theo `available_actions` của từng dòng (BE tính cả luật lẫn quyền). FE không tự suy luật.
- Lỗi BE hiện **nguyên văn** `detail`: BR-PQ-08 (SĐT, username, mật khẩu, nhóm lạ), BR-PQ-17 (tự thao tác, thẩm quyền
  Chủ/superuser, 403), BR-PQ-18 (Chủ cuối cùng), BR-GH-08 (còn phiếu Đang giao), BR-PQ-01 (đã nghỉ / đang làm).
  Form dùng `noValidate` để lỗi luôn đến từ BE.
- Hỏi xác nhận trước: cho nghỉ; thêm hoặc bỏ nhóm Chủ (khi đổi nhóm và khi tạo tài khoản có nhóm Chủ).
- Form tạo tài khoản **giữ nháp** (`useDraft`, khoá `staff:create`, S7-AC6). Mật khẩu **không** lưu vào nháp.
- Mật khẩu tạm (S48): ô chung `shared/ui/PasswordInput` (mặc định ẩn, nút mắt ≥44px, gợi ý quy tắc) + ô "Nhập lại";
  lệch → "Hai mật khẩu không khớp", KHÔNG gọi API. "Tạo ngẫu nhiên" điền cả hai ô và hiện chữ. Tạo xong hoặc đặt lại xong
  thì hiện mật khẩu để Chủ đọc cho nhân viên; BE bật `must_change_password` → lần đăng nhập đầu nhân viên phải đổi.
- Nháp form tạo (`useDraft`, khoá `staff:create`) KHÔNG chứa mật khẩu; nháp được áp ngay lần render đầu (sửa flake Q2),
  nút "Tạo tài khoản" chỉ khoá khi đang gửi.
- Mock (`mock.ts`) mô phỏng đúng bảng lỗi, thứ tự kiểm và `available_actions` của BE, dùng chung kho người dùng mock
  của `features/auth` (tạo xong đăng nhập được, cho nghỉ thì token cũ 401). `giao2` còn 2 phiếu Đang giao (BR-GH-08),
  `ql9` có `manage_staff` nhưng không thuộc Chủ (BR-PQ-17), `sa1` là superuser + Quản lý (BR-PQ-18).

| File | Làm gì |
|---|---|
| `api.ts` | 7 hàm API + `filterStaff` (tìm bỏ dấu) + `suggestPassword` |
| `mock.ts` | `mockStaffApi` — một handler cho mọi đường `/api/staff/…` |
| `types.ts` | `StaffMember`, `StaffAction`, `StaffFilter`, input/kết quả |
| `components/StaffScreen.tsx` | danh sách hàng thoáng (avatar chữ cái, nhãn nhóm, chấm trạng thái, nút gọi) + lọc + tìm + khung xương khi tải + rỗng + thông báo nổi |
| `components/StaffDetail.tsx` | chi tiết một người trong tấm bên (tiêu đề đổi theo bước) và các thao tác (sửa, đổi nhóm, đặt lại MK, cho nghỉ/làm lại) |
| `components/StaffCreateForm.tsx` | form tạo tài khoản một cột, 3 phần, thanh nút dính đáy (giữ nháp) |
| `components/GroupPicker.tsx`, `PasswordField.tsx`, `CopyButton.tsx` | thẻ ô chọn nhóm; cặp ô mật khẩu tạm + nhập lại + "Tạo ngẫu nhiên" + "Sao chép"; nút chép có phản hồi |
| `components/parts.tsx` | avatar, nhãn nhóm, chấm trạng thái, dòng lỗi BE, `DangerConfirm`, `Credentials`, `useFocusOnSwap` |
| `staff.module.css` | toàn bộ kiểu của màn (UI4), chỉ token |

Móc e2e (tên lớp thường, không có kiểu ở globals.css): `ul.staff-list > li`, `.staff-open`, `.group-tag`, `.staff-actions`,
`.confirm-danger`, `.cred-username`, `.cred-password`. Tấm bên + thông báo nổi dùng `shared/ui/SideSheet.tsx`, `shared/ui/Toast.tsx` (đưa lên dùng chung ở UI5).
