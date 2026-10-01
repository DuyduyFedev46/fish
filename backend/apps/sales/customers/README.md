# sales/customers — Khách hàng (7.1)

Guest checkout: khách gộp theo số điện thoại (`services.get_or_create_by_phone`, dùng bởi `orders.create_order`).
NV giao chỉ thấy khách của phiếu giao gán cho mình (BR-PQ-12, test ở `apps/common/tests/test_s5_scope_nv_giao.py`).
Endpoint: `/api/sales/customers/`.

## Danh bạ khách cho ERP (Lô 6 / B2, BR-PQ-31)
- `GET /api/sales/customer-directory/` · `GET|PATCH /api/sales/customer-directory/{id}/` (`directory_api.py`).
  Quyền Tầng 2 `sales.view_customer_list` ("Xem khách hàng"; owner + manager, migration `sales/0013`); `PATCH` thêm `sales.change_customer`.
- `permissions.py::can_view_customer_directory`: MỘT hàm quyền cho danh bạ, dòng thời gian `customer` (`next_steps.py`) và
  lọc `?customer=` của danh sách đơn (`orders/scope.py`). Không tự kiểm tên Group ở nơi khác.
- `services.update_customer_profile`: chỉ sửa `name`, `default_address`, `note`; SĐT khoá. AuditLog `update_customer` chỉ ghi tên trường.
- Endpoint cũ `/api/sales/customers/` (S5, CS-01, NV giao xem khách của phiếu mình) giữ nguyên.
