# accounts/auth — Đăng nhập, "tôi là ai" (§1, UC-01)

- Đăng nhập token: view có sẵn của DRF `POST /api/auth/token/` (khai ở `config/api_urls.py`).
- `GET /api/auth/me/` (S6, BR-PQ-09): `api.MeView` → `services.describe_user(user)` trả
  `id, username, display_name, phone, groups, permissions, can_view_cost, can_view_profit, home`.
  `home`: không Group → `no-role`; chỉ `nv_giao` → `my-deliveries`; còn lại → `dashboard`.
  `display_name`/`phone` lấy từ `StaffProfile` (không có hồ sơ → username / "").
- 401 (chưa đăng nhập, token hỏng/đã thu, `is_active=False`): `{"detail": "Thông tin xác thực không hợp lệ."}`
  — đặt ở `apps/common/api.exception_handler`.
- S47: `me` thêm `group_labels` [{code,label}] (theo thứ tự vai) và `capabilities` [{code,label}]
  = quyền Tầng 2 người đó đang có, lấy theo `services.CAPABILITY_LABELS` (spec §1.5 + mọi
  `Meta.permissions`; thứ tự dict = thứ tự hiển thị). Thêm quyền Tầng 2 mới → thêm nhãn ở đó
  (có test đỏ nếu quên). Tính lại mỗi lần gọi → đổi nhóm có hiệu lực ngay.
- S46 (C8: một token mỗi người):
  - `POST /api/auth/logout/` → 204; `services.logout` xoá token (mọi máy văng), đóng session nếu có,
    AuditLog `logout`.
  - `POST /api/auth/change-password/` `{"old_password","new_password"}` → 200 `{"token": mới}`;
    `services.change_own_password`: kiểm mật khẩu cũ (`AUTH_OLD_PASSWORD`) → `validate_password`
    (`AUTH_WEAK_PASSWORD`, thông điệp tiếng Việt) → đổi, xoá token cũ, cấp token mới, AuditLog
    `password_change_self` (không chứa mật khẩu). Field khác → 400 `BR-PQ-17`.
- S48 (BR-PQ-19): `me` thêm `must_change_password` (superuser luôn `false`). Cờ
  `StaffProfile.must_change_password` bật khi Chủ tạo tài khoản / đặt lại mật khẩu, tắt khi tự đổi
  (change-password). Khi bật, `authentication.py` (lớp bọc Token/Session của DRF, khai trong
  `REST_FRAMEWORK.DEFAULT_AUTHENTICATION_CLASSES`) trả 403
  `{"detail", "code": "AUTH_MUST_CHANGE_PASSWORD"}` cho mọi view DRF, trừ view có
  `allow_must_change_password = True` (token, me, logout, change-password).
  Lưu ý test: `force_authenticate` bỏ qua lớp xác thực → test S48 dùng token thật.
- QA lần 2: mật khẩu mới trùng mật khẩu hiện tại → 400 `AUTH_WEAK_PASSWORD` "Mật khẩu mới phải khác mật khẩu hiện tại." (B4). `middleware.AdminMustChangePasswordMiddleware` chặn Django Admin (403 + hướng dẫn đặt mật khẩu qua ERP) khi còn cờ; login/logout Admin vẫn mở; superuser không bị ép (B3). Test: `tests/test_qa2_fixes.py`.
- `tests/test_s6_me.py`, `tests/test_s46_logout_password.py`, `tests/test_s47_me_labels.py`,
  `tests/test_s48_must_change_password.py`.
