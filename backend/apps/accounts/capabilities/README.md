# accounts/capabilities — ma trận phân quyền (B4)

Chủ bật/tắt "việc" cho từng nhóm trên màn Phân quyền. Mỗi việc = một tập permission Django; không có model hay
migration mới (dùng `auth.Group` / `Permission`). Quy tắc BR-PQ-32 (đề xuất): việc "Chỉ Chủ" không cấp cho nhóm khác.

| File | Làm gì |
|---|---|
| `registry.py` | Nguồn duy nhất: danh sách việc (`key`, nhãn, khu, `perms`, `owner_only`, `requires`) + bảng phạm vi dữ liệu theo nhóm (cột `customers` tính theo quyền thực tế). |
| `services.py` | `list_groups`, `describe_group` (đọc); `set_group_capabilities` (ghi việc + phạm vi, khoá lạc quan `version`, xác nhận mở rộng dữ liệu khách, chống leo quyền, ghi `AuditLog`) và `preview_group` (xem trước, không ghi). |
| `api.py` | `GET /api/staff/groups/`, `GET /api/staff/groups/{code}/`, `PUT /api/staff/groups/{code}/capabilities/` (thân `{version, capabilities?, scopes?, confirm_customer_data_widening?}`), `POST /api/staff/groups/{code}/permissions-preview/`. |
| `next_steps.py` | Provider guidance `group` (dòng thời gian của nhóm) cho `GET /api/guidance/group/{pk}/`. |
| `tests/` | Registry (codename tồn tại, các việc rời nhau), đọc, ghi, leo quyền, dòng thời gian, quyền của nhóm Nhân viên giao. |

Luật ghi: chỉ nhóm Chủ ghi được · nhóm `owner` khoá · không bật việc `owner_only` cho nhóm khác · chỉ đụng permission
trong registry · việc có `requires` (`pack_print` cần `deliver`) phải bật/tắt cùng việc gốc, lệch thì 400 `CAPABILITY_REQUIRES` · mỗi thay đổi ghi `AuditLog` `change_group_capabilities` (`changes` chỉ có mã việc và trạng thái).
Thêm một việc mới: thêm vào `registry.CAPABILITIES`; test registry bắt codename sai và việc trùng permission.
Thêm cặp phụ thuộc: khai `requires=(...)` ở việc phụ thuộc; test `test_requires.py` quét mọi `@action(required_perms=...)` để bắt action đòi quyền của hai việc mà chưa khai.
