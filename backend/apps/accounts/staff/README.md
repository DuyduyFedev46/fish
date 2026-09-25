# accounts/staff — Quản lý nhân viên (S41, S42 · UC-23)

Chủ (quyền `accounts.manage_staff`) tạo tài khoản `User` + `StaffProfile`, gán/bỏ Group cộng dồn,
sửa tên/SĐT, cho nghỉ, cho làm lại, đặt lại mật khẩu. Không xoá tài khoản (BR-PQ-02).

| File | Làm gì |
|---|---|
| `services.py` | Nghiệp vụ: `create_staff`, `update_profile`, `set_groups`, `deactivate`, `reactivate`, `reset_password`, `available_actions` |
| `api.py` | `StaffViewSet` → `/api/staff/` (+ `groups/`, `deactivate/`, `reactivate/`, `reset-password/`) |
| `serializers.py` | `staff_item()`: JSON một dòng, dựng tường minh, không có mật khẩu/hash/token |
| `tests/` | `test_s41_staff.py`, `test_s42_staff.py`, `test_s41_admin.py`, `test_q1_concurrency.py` |

Rule: **BR-PQ-17** không tự đổi nhóm / tự cho nghỉ / tự đặt lại mật khẩu; chỉ Chủ hoặc superuser
đụng nhóm `chu` và tài khoản Chủ (403); chỉ superuser đụng tài khoản superuser.
**BR-PQ-18** luôn còn ≥ 1 Chủ đang làm. **BR-GH-08** còn phiếu Đang giao thì không cho nghỉ.
Cho nghỉ / đặt lại mật khẩu xoá token (C8: mọi máy của người đó văng ngay). Mọi thay đổi ghi AuditLog
`staff_create`, `staff_update`, `staff_groups_change`, `staff_deactivate`, `staff_reactivate`,
`staff_password_reset`. Log không chứa mật khẩu. Mật khẩu kiểm theo `AUTH_PASSWORD_VALIDATORS`.
**BR-PQ-19** (S48): tạo tài khoản / đặt lại mật khẩu bật `must_change_password` (mật khẩu Chủ đặt là tạm).
Đồng thời (QA Q1): trùng username lúc insert (`IntegrityError`) → 400 `BR-PQ-08`; `set_groups` và
`deactivate` khoá MỘT lần theo pk tăng dần gồm người đích + mọi Chủ đang làm
(`_lock_target_and_chus`) → hai Chủ cho nghỉ nhau cùng lúc không khoá chéo.
