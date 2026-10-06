# data_scopes — phạm vi dữ liệu cấu hình theo nhóm (Tầng 3)

Hồ sơ: `doc/features/2026-10-02-pham-vi-du-lieu-cau-hinh/` (BR-PQ-33/34/36). Thay bảng phạm vi cố định cũ bằng cấu hình
Chủ sửa được trên màn Phân quyền. Mốc hành vi nằm ở `tests/scope_snapshot_baseline.json` (PV-01).

| File | Việc |
|---|---|
| `catalog.py` | Danh mục D1..D8: lựa chọn, `rank`, mặc định, quyền cổng. Dữ liệu thuần, không import model. |
| `resolver.py` | `resolve_data_scopes(user)` / `resolve_data_scope(user, key)`: giá trị rộng nhất trong các nhóm đủ điều kiện; nhớ trên đối tượng user; tối đa 3 truy vấn. |
| `services.py` | Dựng `data_scopes`, `data_scope_values`, `scopes` cũ cho GET `/api/staff/groups/`. Hàm ghi thêm ở Lô 5. |
| `tests/` | Ảnh chụp mốc (PV-01), catalog, resolver, migration gieo, GET. |

Lô 2 (PV-02) chưa có màn nghiệp vụ nào đọc resolver; PV-03 → PV-07 chuyển từng đường đọc sang hàm phạm vi theo đối tượng.

Sinh lại mốc khi CỐ Ý đổi hành vi (đọc diff trước khi commit):
`UPDATE_SCOPE_SNAPSHOT=1 python manage.py test apps.accounts.data_scopes.tests.test_scope_snapshot`.
