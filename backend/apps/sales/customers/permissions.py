"""
Quyền "Xem khách hàng" — MỘT nguồn duy nhất (B2, BR-PQ-31, Lô 6).

`sales.view_customer_list` là quyền Tầng 2 (khác `sales.view_customer` là quyền Tầng 1, phạm vi dòng của NV giao).
Mặc định cấp cho `owner` và `manager` (migration `sales/0013`); Chủ bật/tắt cho từng người qua ma trận phân quyền.

Mọi chỗ cần hỏi "người này xem được danh bạ khách không" phải gọi `can_view_customer_directory`, không tự kiểm tên Group:
- `directory_api.py` (danh bạ khách, B2);
- `next_steps.py` (dòng thời gian `customer`, Lô 2 R2);
- `orders/scope.py::can_filter_orders_by_customer` (lọc `?customer=` của danh sách đơn, Lô 3 R3).
"""
VIEW_CUSTOMER_LIST_PERM = "sales.view_customer_list"
CHANGE_CUSTOMER_PERM = "sales.change_customer"


def can_view_customer_directory(user) -> bool:
    """True khi `user` đã đăng nhập và có quyền Tầng 2 "Xem khách hàng" (superuser luôn có)."""
    return bool(user and user.is_authenticated and user.has_perm(VIEW_CUSTOMER_LIST_PERM))
