"""
Phạm vi dòng (Tầng 3) của khách hàng — MỘT nguồn duy nhất, đọc từ cấu hình D7 (PV-05, BR-PQ-33/34/35, bất biến 9).

Dùng cho danh bạ khách mới (`directory_api.py`), API khách cũ (`api.py`), dòng thời gian khách (`next_steps.py`) và lọc
đơn theo khách (`orders/api.py`), nên các đường trả CÙNG một tập khách (PV-05-AC4/AC5).

- `all` (mặc định Quản lý; Chủ, superuser): mọi khách.
- `assigned_deliveries` (mặc định NV giao): khách của đơn có phiếu giao gán cho mình còn trong cửa sổ SR-PII-02
  (`delivery.pii_scope.courier_visible_note_q`, không đổi số ngày).
- `none` (hẹp nhất, mặc định NV kho và CSKH): không khách nào.
Cổng quyền (Tầng 1/2: `view_customer_list` cho danh bạ, `view_customer` cho API cũ) vẫn đứng trước ở từng view (BR-PQ-34).
"""
from apps.accounts.data_scopes.resolver import resolve_data_scope
from apps.delivery.models import DeliveryNote
from apps.delivery.pii_scope import courier_visible_note_q
from apps.sales.models import SalesOrder

ALL = "all"
ASSIGNED_DELIVERIES = "assigned_deliveries"
NONE = "none"


def customers_scope_value(user) -> str:
    """Giá trị D7 "Khách hàng" của `user`."""
    return resolve_data_scope(user, "customers")


def sees_all_customers(user) -> bool:
    """True khi D7 = `all`: được xem đủ hồ sơ khách (địa chỉ mặc định, ghi chú nội bộ)."""
    return customers_scope_value(user) == ALL


def scope_customers_for(user, qs, *, value=None):
    """Lọc queryset `Customer` theo phạm vi D7 của `user`. Không dùng `distinct` để giữ nguyên annotate và thứ tự của `qs`."""
    value = value or customers_scope_value(user)
    if value == ALL:
        return qs
    if value == ASSIGNED_DELIVERIES:
        visible_notes = DeliveryNote.objects.filter(courier_visible_note_q(user))
        customer_ids = SalesOrder.objects.filter(invoice__delivery_notes__in=visible_notes).values("customer_id")
        return qs.filter(pk__in=customer_ids)
    return qs.none()
