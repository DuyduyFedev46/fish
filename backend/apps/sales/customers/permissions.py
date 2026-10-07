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


# PV-07 (BR-PQ-38): việc V2 "Xem thông tin khách trên đơn, hoá đơn, phiếu hoàn tiền". Khác `view_customer_list` ở trên: V2 chỉ điều khiển
# ô tên, SĐT, địa chỉ trên đơn, hoá đơn bán, phiếu hoàn tiền; danh bạ khách và phiếu giao có luật riêng (D7, D3 + cửa sổ).
VIEW_ORDER_CUSTOMER_INFO_PERM = "sales.view_order_customer_info"

HIDDEN_NOT_PERMITTED = "not_permitted"
HIDDEN_EXPIRED = "expired"


def can_view_order_customer_info(user) -> bool:
    """True khi `user` đã đăng nhập và có V2 (superuser luôn có)."""
    return bool(user and user.is_authenticated and user.has_perm(VIEW_ORDER_CUSTOMER_INFO_PERM))


def customer_hidden_reason(user, obj):
    """Lý do che ô khách trên đơn, hoá đơn, phiếu hoàn (02b §2.7): None | "not_permitted" | "expired".

    "not_permitted" (không có V2) đứng trước "expired" (`pii_visible=False`, quá cửa sổ SR-PII-02). Queryset không gắn
    `pii_visible` (nhóm ở phạm vi "Tất cả") thì coi như còn trong cửa sổ."""
    if not can_view_order_customer_info(user):
        return HIDDEN_NOT_PERMITTED
    if getattr(obj, "pii_visible", True) is False:
        return HIDDEN_EXPIRED
    return None
