# features/permissions — Phân quyền

Story: **ED-40** (ma trận việc x nhóm, trang nhóm); ED-39 là phần BE (`/api/staff/groups/…`, đã có). Quyết định của Duy (#13):
quyền do admin cấu hình được; Chủ có thể bật "Xem khách hàng" cho nhóm bất kỳ, và khi bật thì màn **phải** ghi rõ "Tất cả khách".

Route: `/permissions/` (ma trận) và `/permissions/detail/?group=<mã nhóm>` (một nhóm). Bọc `<ViewGuard view="permissions">`
(cần `accounts.manage_staff`). Mọi người có quyền xem đều xem được; **chỉ người thuộc nhóm Chủ** thấy công tắc bấm được
(superuser ngoài nhóm Chủ xem ở chế độ chỉ đọc: BE cho cả Chủ và superuser ghi, FE chặt hơn một cách có chủ ý,
không phải do BE chặn).

## Contract BE (B4, R16: dưới `/api/staff/groups/`, khác chữ ở story)

| Hàm (`api.ts`) | Endpoint |
|---|---|
| `listGroups()` | `GET /api/staff/groups/` → nhóm kèm trạng thái từng việc |
| `getGroup(code)` | `GET /api/staff/groups/<code>/` → thành viên, registry các việc, phạm vi dữ liệu, dòng thời gian |
| `setGroupCapabilities(code, changes)` | `PUT /api/staff/groups/<code>/capabilities/` → chi tiết nhóm mới |

Thêm / bỏ thành viên đi qua `PUT /api/staff/{id}/groups/` của module `staff` (một chỗ duy nhất đổi nhóm của một người).

## Luật FE

- Registry (danh sách việc, mục, khoá `requires`, "Chỉ Chủ") lấy từ `getGroup("owner")`, không gõ lại ở FE.
- Công tắc `role="switch"` tên `"<Việc> — <Nhóm>"`. Bật/tắt có hiệu lực ngay; chỉ **tắt việc phá luồng** (`view_orders`,
  `deliver`, `view_audit`) mới hỏi lại kèm số người bị ảnh hưởng (`breakingWarning`).
- Việc có `requires`: bật/tắt đi cùng yêu cầu với việc gốc (`planToggle`), tất cả hoặc không gì cả.
- Cột nhóm Chủ cố định (không có công tắc). Việc "Chỉ Chủ" của nhóm khác khoá, không có công tắc (BR-PQ-32).
- "Xem khách hàng" đang bật ở nhóm khác Chủ: nhãn "Tất cả khách" hiện ngay trong ô (`ALL_CUSTOMERS_LABEL`).
- Lỗi BE hiện nguyên văn `detail`. Không cập nhật "lạc quan": ô chỉ đổi khi BE đã nhận, nên không bao giờ hiện quyền chưa lưu.
- Mock (`mock.ts`) giữ đủ luật BE: chỉ Chủ ghi, nhóm Chủ khoá, không cấp việc "Chỉ Chủ", `CAPABILITY_REQUIRES`. Thay đổi
  được giữ trong `sessionStorage` (khoá `cave_erp_mock_group_caps`, chỉ khoá việc → true/false) và **không** làm đổi quyền
  lúc đăng nhập mock. Thành viên lấy từ kho người dùng mock của `features/auth`.

## File

| File | Làm gì |
|---|---|
| `api.ts` · `mock.ts` · `types.ts` · `messages.ts` | API (kèm mock), kiểu, chữ UI một chỗ |
| `permissionsModel.ts` (+ test) | hàm thuần: chia mục, `cellMode`, `planToggle`, cảnh báo phá luồng, tìm bỏ dấu, `groupHref`, đọc `?group=` |
| `useCapabilityToggle.ts` | bật/tắt dùng chung ma trận và trang nhóm (hỏi lại khi cần, khoá ô đang gửi, đổi ô khi BE đã nhận) |
| `useGroupData.ts` | tải danh sách nhóm / một nhóm (dùng bộ tải của `features/staff/useLoaded.ts`) |
| `components/PermissionMatrixScreen.tsx` | ma trận, tìm việc, cột nhóm có link tới trang nhóm |
| `components/GroupDetailScreen.tsx` | trang nhóm: việc được làm, phạm vi dữ liệu, thành viên, dòng thời gian |
| `components/PermSwitch.tsx` · `ConfirmOffModal.tsx` · `AddMemberModal.tsx` · `RemoveMemberModal.tsx` | công tắc, hộp hỏi lại, thêm / gỡ thành viên |
| `permissions.module.css` | kiểu của module (chỉ token) |

Kịch bản: `e2e/ed_batch14_permissions.py` (mock, kèm 403, ngoài đường thuận, mobile 360).
