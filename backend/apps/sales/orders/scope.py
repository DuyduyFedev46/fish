"""
Phạm vi dòng (Tầng 3) của đơn hàng — MỘT nguồn duy nhất (P8 SR-06, BM-03).

`SalesOrderViewSet.get_queryset`, khối Tiếp theo · Đã làm của đơn (`next_steps.py`) và việc
"Nhờ" (`ai/actions/services.py::escalate_guidance_step`, qua provider) đều gọi hàm này để
không lệch nhau.

PV-03 (Lô 3): phạm vi lấy từ cấu hình D1 của nhóm (`data_scopes.resolver`), không còn gắn cứng với tên nhóm.
- `all` (mặc định Chủ, Quản lý, NV kho; superuser): thấy mọi đơn.
- `assigned_deliveries` (mặc định NV giao): chỉ đơn của phiếu giao gán cho mình (BR-PQ-12, S5).
- `assigned_or_confirmation` (mặc định CSKH): đơn của phiếu gán cho mình, hoặc đơn của phiếu trong phạm vi gọi hay đơn
  mình đã gọi gần đây (BR-GH-18, CS-01).
- User không nhóm (gán quyền trực tiếp): hẹp nhất = `assigned_deliveries` (UC-6).
"""
from django.db.models import Exists, OuterRef, Q

from apps.accounts.data_scopes.resolver import resolve_data_scope
from apps.delivery.models import DeliveryNote
from apps.sales.customers.permissions import can_view_customer_directory

ALL = "all"
ASSIGNED = "assigned_deliveries"
ASSIGNED_OR_CONFIRMATION = "assigned_or_confirmation"


def orders_scope_value(user) -> str:
    """Giá trị D1 "Đơn hàng" của `user` (phân giải từ cấu hình nhóm, BR-PQ-33/34)."""
    return resolve_data_scope(user, "orders")


def scope_orders_for(user, qs, *, value=None):
    """Lọc queryset `SalesOrder` theo phạm vi của `user`. Không đổi thứ tự/annotate của `qs`.

    `value` mặc định là D1 của `user`; hoá đơn truyền D2 (cùng bộ giá trị, theo D1 của nhóm có quyền xem hoá đơn)."""
    value = value or orders_scope_value(user)
    if value == ALL:
        return qs

    assigned_q = Q(invoice__delivery_notes__assigned_to=user)
    if value == ASSIGNED_OR_CONFIRMATION:
        from apps.delivery.confirmation.scope import customer_service_note_q

        confirmation_q = Exists(
            DeliveryNote.objects.filter(
                sales_invoice__sales_order=OuterRef("pk")
            ).filter(customer_service_note_q(user))
        )
        return qs.filter(assigned_q | confirmation_q).distinct()

    return qs.filter(assigned_q).distinct()


def can_filter_orders_by_customer(user) -> bool:
    """Lọc đơn theo khách (`?customer=`) là xem dữ liệu khách: đòi quyền "Xem khách hàng" (02b §3.8 R3).

    Dùng hàm chung `can_view_customer_directory` (`sales.view_customer_list`, B2/Lô 6) để không lệch với
    danh bạ khách và dòng thời gian khách."""
    return can_view_customer_directory(user)
