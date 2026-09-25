# sales/customers — Khách hàng (7.1)

Guest checkout: khách gộp theo số điện thoại (`services.get_or_create_by_phone`, dùng bởi `orders.create_order`).
NV giao chỉ thấy khách của phiếu giao gán cho mình (BR-PQ-12, test ở `apps/common/tests/test_s5_scope_nv_giao.py`).
Endpoint: `/api/sales/customers/`.
