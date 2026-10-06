# Phạm vi dữ liệu cấu hình — Ghi chú dev (03)
> be-dev · 2026-10-06 · nhánh `feat/pham-vi-du-lieu` (tách từ main `fa2368f`). Mục BE. Chưa push, chưa merge main.

## Lô 1 — PV-01 (ảnh chụp mốc), commit `bc32ebc`

Chỉ thêm file, không sửa code sản phẩm: `backend/apps/accounts/data_scopes/__init__.py` và `data_scopes/tests/`.

| File | Việc |
|---|---|
| `tests/fixtures.py` | Dữ liệu giả: 11 tài khoản (Chủ, Quản lý, NV kho, 2 NV giao, 2 CSKH, K+G, người không nhóm có quyền gán trực tiếp, superuser, ẩn danh), 16 đơn (mỗi đơn một khách), phiếu giao đủ trạng thái, 3 phiếu hàng hoàn, 5 phiếu nhập quanh nửa đêm giờ VN, 2 phiếu hoàn tiền. Giờ cố định 06/10/2026 10:00 giờ VN. |
| `tests/snapshot.py` | Bộ thu: gọi từng endpoint bằng từng tài khoản, ghi **sự kiện** (`status=`, `visible:<nhãn>`, `status:<nhãn>=404`, `pii:<nhãn>:<đường dẫn>` chỉ có/không giá trị, `extra:`). `diff_snapshots`, `APPROVED_DIFFS`. |
| `tests/test_scope_snapshot.py` | 9 test: AC1 (khớp mốc, đủ tài khoản × endpoint), AC2 (đổi luật thật bằng mock thì đỏ, in tài khoản/endpoint/dòng; mất quyền cũng là lệch), AC3 (đúng một ngoại lệ), AC4 (grep tệp mốc không có tên/SĐT/địa chỉ giả), tính tất định. |
| `tests/scope_snapshot_baseline.json` | Tệp mốc, sinh bằng `UPDATE_SCOPE_SNAPSHOT=1` trên code cũ. |

Endpoint trong mốc (mỗi nhóm gọi × 11 tài khoản): đơn (danh sách, chi tiết, tìm `?q=` theo SĐT và theo tên, lọc `?customer=`), hoá đơn bán (danh sách + tổng, chi tiết), phiếu hoàn tiền, phiếu giao (danh sách, `assigned_to=me`, `assigned_to=<người khác>`, chi tiết), hàng hoàn, phiếu nhập, hàng chờ gọi xác nhận (mặc định, `DONE`, `ESCALATED`, chi tiết, tìm theo SĐT), danh bạ khách mới (danh sách, `search`, chi tiết), `/customers/` cũ, dòng thời gian của đơn, phiếu giao, hàng hoàn, khách, phiếu nhập, dashboard, lệnh AI đọc đơn và phiếu giao. Xuất file: grep không thấy endpoint xuất CSV/XLSX (đúng với 02b §1.5) nên không có mục.

Lưu ý khi đọc mốc:
- `ai.orders_list` bị cắt theo `AI_RESULT_MAX_CHARS` (12/16 đơn): tất định nhưng chỉ phủ 12 dòng đầu; từng đơn vẫn được phủ riêng ở `ai.orders_detail`.
- Mốc ghi hành vi HIỆN TẠI kể cả chỗ lạ: người không nhóm có quyền xem đơn trực tiếp thấy 1 đơn (đơn gán cho mình) nhưng mở hàng chờ gọi xác nhận thì mọi chi tiết đều 404; NV kho hôm nay chưa thấy tên khách trên hoá đơn (ngoại lệ duyệt Q-4); `deliveries.other` của NV giao khác mình trả 403.
- Ngoại lệ duy nhất: `("warehouse_staff", "invoices.list", "+", "pii:*:customer_name")`, ghi "Duy duyệt 02/10 Q-4".
- Mốc dùng nhãn fixture, không pk. Chạy 2 lần cho cùng kết quả (có test).

## Lô 2 — PV-02 (cấu hình, resolver, GET)

### File đã sửa / thêm
- `backend/apps/accounts/models.py`: thêm `GroupAccessConfig`, `GroupDataScope` (đúng 02b §3).
- `backend/apps/accounts/migrations/0014_group_data_scopes.py` (schema, tự sinh), `0015_seed_group_data_scopes.py` (data).
- `backend/apps/accounts/data_scopes/catalog.py`, `resolver.py`, `services.py`, `README.md`.
- `backend/apps/accounts/capabilities/services.py` (thêm `version`, `data_scope_values`, `data_scopes`; `scopes` cũ dựng từ cấu hình), `registry.py` (bỏ `GROUP_SCOPES` và hằng `SCOPE_*`).
- Test mới: `data_scopes/tests/test_catalog.py`, `test_resolver.py`, `test_seed_migration.py`, `test_api_describe.py` (59 test mới). Sửa 2 file test cũ cho hợp khoá mới: `capabilities/tests/test_api_read.py` (thêm khoá vào `LIST_KEYS`, `DETAIL_EXTRA`), `test_registry.py` (test `GROUP_SCOPES` đổi sang kiểm `catalog.DEFAULT_GROUPS`).

### Endpoint (chỉ THÊM khoá, theo 02b §2.1, §2.2)
`GET /api/staff/groups/` mỗi nhóm thêm `"version": "1"` và `"data_scope_values": {"orders": "all", "deliveries": "all", "confirmation": "all_pending", "returns": "all", "receipts": "all", "customers": "all"}`.
`GET /api/staff/groups/<code>/` thêm `version`, `data_scope_values` và `data_scopes` (8 dòng D1..D8: `key, label, value, editable, customer_data, gate_capability, inactive_reason, note, options[{value,label,rank}]`). Ví dụ nhóm `delivery_staff`, dòng đơn:

```json
{"key": "orders", "label": "Đơn hàng", "value": "assigned_deliveries", "editable": true, "customer_data": true,
 "gate_capability": "view_orders", "inactive_reason": null, "note": null,
 "options": [{"value": "assigned_deliveries", "label": "Đơn có phiếu giao gán cho tôi", "rank": 0},
             {"value": "assigned_or_confirmation", "label": "Đơn có phiếu gán cho tôi hoặc trong phạm vi gọi xác nhận", "rank": 1},
             {"value": "all", "label": "Tất cả đơn", "rank": 2}]}
```
Quyền đọc không đổi (`CanManageStaff`; NV kho, NV giao, CSKH, Quản lý không có `manage_staff` → 403; chưa đăng nhập → 401).

### Migration
- `0014`: tạo 2 bảng. Lùi = `migrate accounts 0013` (xoá bảng).
- `0015`: gieo `GroupAccessConfig(row_version=1)` cho 5 nhóm và 24 dòng `GroupDataScope` (4 nhóm × 6 đối tượng; `owner` không có dòng). Giá trị chép cứng, `get_or_create` không ghi đè, D7 = `all` nếu nhóm **đang có** `sales.view_customer_list` lúc migrate. Không đụng `auth_group_permissions`. Phụ thuộc `accounts/0014` và `sales/0013`.
- Đã chạy thật trên SQLite tạm: `migrate` từ DB trống OK (5 cấu hình, 24 dòng; D7: manager `all`, delivery_staff `assigned_deliveries`, warehouse_staff và customer_service `none`), `migrate accounts 0013` lùi OK (2 bảng mất), `migrate` tiến lại OK, `makemigrations --check --dry-run` sạch.

### Rule BR đã cài / đã thể hiện
- BR-PQ-33 (cấu hình theo nhóm, mặc định = hiện trạng): catalog + migration 0015, test `defaults == seed == bảng contract`.
- BR-PQ-34 (rộng nhất trong các nhóm đủ điều kiện): `resolver.resolve_data_scopes`. Test R1b: người K+G, K tắt `view_orders` mà D1 lưu `all` → chỉ đơn gán (G).
- UC-6 / PV-02-AC4: người không nhóm, nhóm thiếu dòng, giá trị lưu hỏng → rank 0.
- S-5: `owner` và superuser → rộng nhất mọi đối tượng.
- BR-PQ-36: nhớ trên `user._data_scope_cache`; user nạp mới thấy cấu hình mới (có test). Phân giải ≤ 3 truy vấn cho cả 8 đối tượng (có test), người ẩn danh 0 truy vấn.
- Bất biến 1 và 9: mô tả phạm vi chỉ mã và nhãn cố định, test không có giá vốn; Lô 2 không thêm đường đọc dữ liệu khách nào.
- AuditLog và khoá lạc quan: Lô 2 chỉ có cột `row_version` và hiển thị `version`. Ghi (so `row_version`, 409, AuditLog `change_group_data_scopes`) thuộc Lô 5.

### Chứng cứ không đổi hành vi
Test mốc Lô 1 (`test_scope_snapshot`, 9 test) xanh nguyên sau Lô 2 mà không phải sinh lại mốc. Test mới `test_pv02_ac3_default_matrix_per_group_equals_todays_behaviour` ghi ma trận phân giải của 5 nhóm trên DB mới.

### Lệch so với 02b (cần techlead biết)
1. **`default_permissions = ()` cho CẢ HAI model.** 02b chỉ ghi cho `GroupDataScope`. Thêm cho `GroupAccessConfig` để Django không sinh thêm 4 permission `add/change/delete/view` vô chủ (cấu hình chỉ sửa qua service). Test khẳng định không có permission nào của 2 model.
2. **`gate_capability` trả `null` khi mã việc chưa có ở registry**: V1 `view_sales_invoices` chưa tồn tại tới Lô 3 (PV-07), nên dòng `invoices` hiện `gate_capability: null`. Từ Lô 3 tự thành `"view_sales_invoices"` (catalog đã khai sẵn).
3. **`scopes` cũ**: nhãn giữ như hôm nay cho cấu hình mặc định (`Tất cả`, `Được gán`, `Tất cả khách`, `Không xem`) để test cũ và FE không đổi. Khác biệt duy nhất: CSKH ở `orders` nay là "Được gán hoặc trong phạm vi gọi xác nhận" thay chữ cũ "Trong phạm vi gọi"; CSKH ở `deliveries` là "Được gán". `customers` vẫn tính theo quyền thực tế (M2), vì PUT của Lô 2 chưa ghi D7 (PO-Q1 thuộc Lô 5).
4. D2 của owner hiển thị `value: "follows_orders"` (không phải "all") nhưng vẫn có `note: "Chủ luôn thấy tất cả"` và `editable: false`; D8 của owner `value: "all"`.
5. Hàm `catalog.valid_or_narrowest`, `rank_of`, `widest_value`, `narrowest_value`, `ranked_options`, `stored_objects` là hàm phụ thêm (không có trong bảng 02b §1.2), phục vụ resolver và services.

### Việc còn nợ / lưu ý cho lô sau
- **R9 / D-3 (đã quan sát, cần đếm trên production trước deploy):** với nhóm thật, các đối tượng mà nhóm không đủ điều kiện nhận rank 0 (K: gọi xác nhận → `pending_or_called_recently`, khách → `none`; G và C: phiếu nhập → `created_by_me_today`, hoá đơn → `assigned_deliveries`). Tất cả đều nằm sau cổng quyền Tầng 1 nên hôm nay không đường nào lộ; nhưng khi PV-03..PV-07 chuyển đường đọc sang resolver thì người **không nhóm có quyền gán trực tiếp** đổi hành vi theo đúng R9.
- Resolver chưa có chỗ gọi nào ở màn nghiệp vụ (đúng ranh giới PV-02). Hàm phạm vi theo đối tượng (`scope_orders_for(value=)`, ...) là Lô 3..4.
- `backend/README.md` và `apps/accounts/README.md` chưa cập nhật bản đồ module (ngoài danh sách file của 02b); đã có `data_scopes/README.md`.
- Môi trường worktree: thư mục `.claude/worktrees/pham-vi/backend/` không có `.env` và `staticfiles/` (gitignored), nên tôi tạo hai symlink tới bản ở `backend/` chính để chạy test (33 test admin lỗi manifest nếu thiếu `staticfiles`). Symlink không được commit.

## Kiểm chứng (chạy trong lượt làm)
- `manage.py test` toàn bộ trước Lô 1: 2850 test (suy ra 2859 − 9). Sau Lô 1: **2859 test, OK**. Sau Lô 2: **2918 test, OK** (0 failure, 0 error).
- `makemigrations --check --dry-run`: `No changes detected`.
- `migrate` từ DB SQLite trống, lùi `accounts 0013`, tiến lại: OK (xem trên).
- `python3 scripts/check_naming.py`: OK, không phát sinh vi phạm mới.
