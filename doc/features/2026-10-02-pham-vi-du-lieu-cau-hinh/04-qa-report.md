# QA — Phạm vi dữ liệu cấu hình
> qa-tester · nhánh `feat/pham-vi-du-lieu` HEAD eb7fd92. Mọi dữ liệu là dữ liệu giả (`seed_demo` + tài khoản `qa_*`); DB SQLite tạm, đã xoá.

## QA Lô 1–2 BE (06/10)

### Kết luận: APPROVED — lô không đổi hành vi (357 lời gọi API giống hệt main), migration an toàn trên DB có dữ liệu, H1 đã đóng.
### Tổng: 14 ca · ✅ 14 · ❌ 0 · ⏸ 0 (chỉ BE; FE ngoài phạm vi lô này)

| # | Ca | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | Migrate 0013 → head, kịch bản A (mặc định): quyền 5 nhóm không đổi | ✅ | `PERMS IDENTICAL` (so `auth_group_permissions` trước/sau). owner 149, manager 70, warehouse_staff 36, delivery_staff 9, customer_service 4 |
| 2 | Kịch bản B (Chủ đã đổi qua B4: tắt `view_customer_list` của Quản lý; bật cho NV giao và CSKH; tắt `view_salesorder` của NV kho): quyền không đổi, D7 đúng theo quyền lúc migrate | ✅ | `PERMS IDENTICAL`; D7: manager `none`, warehouse_staff `none`, delivery_staff `all`, customer_service `all`. Kịch bản A: manager `all`, warehouse_staff `none`, delivery_staff `assigned_deliveries`, customer_service `none` |
| 3 | Số dòng | ✅ | `config rows 5 scope rows 24` ở cả A và B (owner 0 dòng; 4 nhóm × 6) |
| 4 | Lùi `migrate accounts 0013` rồi tiến lại | ✅ | `Unapplying 0015 OK`, `Unapplying 0014 OK`, bảng mất, quyền y nguyên (`PERMS IDENTICAL after rollback`), tiến lại 5/24; `makemigrations --check` = `No changes detected` |
| 5 | Ngoài đường thuận: thiếu nhóm `customer_service` lúc migrate; dòng đã có sẵn giá trị khác | ✅ | `cfg 4 scopes 18`, không lỗi; dòng `warehouse_staff.orders=none` tạo trước vẫn giữ `none` (không ghi đè) |
| 6 | `GET /api/staff/groups/` + `/<code>/` theo vai (runserver thật, đăng nhập token) | ✅ | Chưa đăng nhập 401; manager, warehouse_staff, delivery_staff, customer_service 403 (cả mã nhóm không tồn tại: 403, không lộ); owner 200; mã lạ 404 `GROUP_NOT_FOUND`. Quyền đọc (`CanManageStaff`) như cũ |
| 7 | Đúng contract §2.2 | ✅ | Danh sách: mỗi nhóm có `version`, `data_scope_values` 6 khoá. Chi tiết: `version`, `data_scope_values`, `data_scopes` 8 dòng (orders, invoices, deliveries, confirmation, returns, receipts, customers, audit_log), mỗi dòng đủ `key,label,value,editable,customer_data,gate_capability,inactive_reason,note,options[{value,label,rank}]`; rank 0 duy nhất mỗi đối tượng |
| 8 | Không giá vốn, không dữ liệu cá nhân trong response | ✅ | grep `rate, landed, unit_cost, purchase, phone, address, customer_name` = không có. Chữ `profit` chỉ là khoá năng lực `view_profit` (on/off). `members` (username nhân viên) đã có ở main, không phải khách |
| 9 | Hồi quy: 357 lời gọi GET (7 danh tính × đơn, khách, danh bạ khách, phiếu giao, gọi xác nhận, hoá đơn, hoàn tiền, hàng hoàn, phiếu nhập, dashboard, `?assigned_to=me`, `?q=`, `?customer=`, chi tiết từng id, timeline) giữa main và nhánh trên cùng dữ liệu | ✅ | Sau chuẩn hoá chữ tiền ("đ" ở main, "₫" ở nhánh) và `as_of`: **0 lệch**, 357/357 trùng cả mã trạng thái lẫn thân JSON. Phân bố: 200×132, 403×104, 404×69, 401×45, 405×6, 400×1. NV giao 2 không thấy phiếu/đơn/khách của NV giao 1 (404); CSKH 403 ở phiếu giao như cũ |
| 10 | H1: NV giao được bật "Xem khách hàng", D7 = `all`, rồi tắt quyền | ✅ | Resolver: mặc định `assigned_deliveries` → bật+`all` = `all` → **tắt quyền (D7 vẫn lưu `all`) = `assigned_deliveries`** → bật lại = `all` |
| 11 | Ngoài đường thuận: người K+G (NV kho + NV giao, K không có `view_customer`) | ✅ | customers `assigned_deliveries` (không mượn `all`), orders `all` (đúng: K có quyền xem đơn) |
| 12 | Ngoài đường thuận: không nhóm / ẩn danh / giá trị lưu hỏng / mất dòng / owner | ✅ | Không nhóm và ẩn danh: toàn rank 0; `orders='garbage'` → `assigned_deliveries`; mất dòng receipts → `created_by_me_today`; owner toàn rộng nhất. Trùng (nhóm, đối tượng) bị `IntegrityError` |
| 13 | API phản ánh DB sống, không nhớ cũ; PUT ghi vẫn bị chặn | ✅ | Sau khi sửa DB: `version 7`, ô mờ có `inactive_reason` khi tắt `view_salesorder`, giá trị hỏng hiển thị rank 0. POST/PUT/PATCH/DELETE `/groups/<code>/` = 405; PUT `/capabilities/` kèm `data_scope_values` = 400 `INPUT_NOT_ALLOWED`, DB không đổi |
| 14 | Test suite | ✅ | `manage.py test apps.accounts` = 415 test OK (gồm 9 test mốc PV-01, 59 test PV-02). Ghi chú môi trường: thiếu symlink `backend/staticfiles` thì 5 test admin lỗi manifest, không liên quan lô. `check_naming.py`: OK. Server đã tắt, symlink và DB tạm đã gỡ |

### Phân quyền (đọc `/api/staff/groups/`)
| Vai | Danh sách | Chi tiết |
|---|---|---|
| Chưa đăng nhập | 401 | 401 |
| owner | 200 | 200 |
| manager, warehouse_staff, delivery_staff, customer_service | 403 | 403 |

Rò giá vốn: không. Rò dữ liệu cá nhân: không (API, log server: 0 Traceback, không có tên, SĐT hay mật khẩu; module mới không có `logger` hay `print`). Hồi quy: ca 9.

### Quan sát (không chặn)
- **O1 (Low, đã biết là nợ L4 Lô 5):** D7 lưu `all` mà nhóm thiếu `view_customer_list`: API hiển thị `value: "all"`, `note: null`, trong khi giá trị hiệu lực là `assigned_deliveries`. Chưa có FE dùng; Lô 5 phải thêm `note`.
- **O2 (Low, đã ghi ở 03-dev-notes lệch #3):** `scopes` cũ của CSKH đổi nhãn ("Trong phạm vi gọi" → "Được gán hoặc trong phạm vi gọi xác nhận" cho đơn, "Được gán" cho phiếu giao). Đây là nhãn hiển thị, không phải quyền: ca 9 chứng minh hành vi truy cập y nguyên. Mock FE cần đồng bộ (L3).
- **O3:** main đã tiến sau điểm tách nhánh: chữ tiền ở dòng thời gian main là "đ", nhánh còn "₫". Không phải do lô này; sẽ tự khớp khi merge.
- Người không nhóm có quyền gán trực tiếp bị rank 0 ở nhiều đối tượng (R9/D-3): chưa có đường đọc nào dùng resolver nên chưa đổi hành vi; cần đếm trên production trước Lô 3.

## Lệnh đã chạy (rút gọn)
- Mỗi kịch bản: `DATABASE_URL=sqlite:///.../migX.sqlite3 manage.py migrate accounts 0013`, migrate từng app khác tới head (để các migration cấp quyền của app khác chạy trước mốc), seed kịch bản B, chụp `auth_group_permissions`, `manage.py migrate`, chụp lại, `cmp`.
- Lùi/tiến: `migrate accounts 0013` → `migrate`; `makemigrations --check --dry-run`.
- Hồi quy: script `APIClient.force_authenticate` chạy trên main (`/backend`) và nhánh, DB main sao chép rồi `migrate` ở nhánh; so JSON.
- API thật: `runserver 8765 --noreload` + `curl` với token của 5 vai.
- H1: `manage.py shell` gọi `resolver.resolve_data_scopes`.
- `manage.py test apps.accounts` (415 OK), `python3 scripts/check_naming.py` (OK).
