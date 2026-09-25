# features/auth — Đăng nhập, phiên, quyền, tài khoản của tôi

Đăng nhập bằng token DRF, tải "tôi là ai" để dựng menu theo quyền, chặn màn khi thiếu quyền, xử lý hết phiên
(giữ nháp), đăng xuất, tự đổi mật khẩu, màn "Tài khoản của tôi". Story: **S7** (khung, contract **S6**),
**S46** (đăng xuất thu hồi phiên, tự đổi mật khẩu), **S47** (màn quyền của tôi, quyền đổi thì console đổi theo),
**S48** (còn mật khẩu tạm → chỉ mở màn "Đặt mật khẩu mới"; ô mật khẩu có mắt, nhập lại, gợi ý quy tắc).

Endpoint (contract thật BE, 03-dev-notes.md "Lô L3–L4" và "Lô L6"):
- `POST /api/auth/token/` — đăng nhập.
- `GET /api/auth/me/` — có `group_labels`, `capabilities` (S47). Tải lại khi mở app, khi quay lại tab sau ≥ 5 phút,
  khi nhận 403. Nếu quyền thật sự đổi sau 403 thì hiện "Quyền của bạn vừa thay đổi" (S47-AC3).
- `POST /api/auth/logout/` → 204. BE xoá mọi token của người đó (một token mỗi người, nên mọi máy bị đăng xuất). Lỗi mạng thì bỏ qua, vẫn xoá token trên máy.
- S48 (contract thật "Lô L6b (BE)"): `me.must_change_password` = true → ConsoleGate / `homePath` đưa về `/set-password/`,
  không mount màn nào khác. API bất kỳ trả 403 `code: AUTH_MUST_CHANGE_PASSWORD` → bật cờ ngay trên máy, tải lại `me`,
  không báo "quyền vừa thay đổi". Đổi xong → `me` tải lại → vào home của vai. Superuser không bị ép (BE trả false).
- `POST /api/auth/change-password/` → 200 `{token}`. Máy này thay token mới, máy khác nhận 401. Lỗi `AUTH_OLD_PASSWORD` /
  `AUTH_WEAK_PASSWORD` / `BR-PQ-17` hiện nguyên văn `detail`.

Dùng từ ngoài: `useAuth()` (AuthProvider), `<ViewGuard view="...">`, `mockRequireUser(req)` cho mock module khác.
Mock module staff dùng chung kho người dùng mock: `mockUsers()`, `saveMockUsers()`, `mockRequireRecord()`, `mockRevokeUserTokens()`.

| File | Làm gì |
|---|---|
| `api.ts` | `login`, `getMe`, `logoutRemote`, `changePassword` |
| `mock.ts` | tài khoản mock (lưu localStorage), quyền theo Group chép từ BE, `group_labels`/`capabilities` theo BE L6, mock logout/đổi mật khẩu; S48: cờ `must_change_password` + cổng chung `setMockGate` trả 403 `AUTH_MUST_CHANGE_PASSWORD` như lớp xác thực BE |
| `types.ts` | `Me`, `TokenResponse`, `ChangePasswordResponse` |
| `session.ts` | id người đăng nhập gần nhất (giữ/xoá nháp, S7-AC6) |
| `components/AuthProvider.tsx` | trạng thái đăng nhập, 401/403 toàn cục, `permNotice`, `changePassword` |
| `components/ConsoleGate.tsx` | cổng vào console, dải "Quyền của bạn vừa thay đổi", link Tài khoản của tôi |
| `components/AccountScreen.tsx` | màn "Tài khoản của tôi" (route `/account/`, kiểu trang cài đặt, `account.module.css`): nhóm, việc được làm, xem giá vốn/lãi lỗ, mục menu, đổi mật khẩu (tấm bên), đăng xuất. Móc e2e: `.who-card .group-tag`, `.cap-list li`, `.perm-yn` |
| `components/ChangePasswordForm.tsx` | form tự đổi mật khẩu (hỏi mật khẩu hiện tại, mới, nhập lại) — dùng cho S46 và S48 (`mustChange`) |
| `components/SetPasswordScreen.tsx` | S48 màn "Đặt mật khẩu mới" (route `/set-password/`), có nút Đăng xuất |
| `components/LoginScreen.tsx`, `NoRoleScreen.tsx`, `RootRedirect.tsx`, `ViewGuard.tsx` | đăng nhập, chưa phân quyền, chuyển hướng "/", chặn màn thiếu quyền |
