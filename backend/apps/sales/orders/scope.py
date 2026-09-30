"""
Phạm vi dòng (Tầng 3) của đơn hàng — MỘT nguồn duy nhất (P8 SR-06, BM-03).

`SalesOrderViewSet.get_queryset`, khối Tiếp theo · Đã làm của đơn (`next_steps.py`) và việc
"Nhờ" (`ai/actions/services.py::escalate_guidance_step`, qua provider) đều gọi hàm này để
không lệch nhau.

- Chủ / Quản lý / NV kho / superuser (`has_full_delivery_scope`): thấy mọi đơn.
- NV giao: chỉ đơn của phiếu giao gán cho mình (BR-PQ-12, S5).
- CSKH: đơn của phiếu trong phạm vi gọi hoặc đơn mình đã gọi gần đây (BR-GH-18, CS-01).
- User khác (gán quyền trực tiếp, không Group): như NV giao (chỉ phiếu gán cho mình).
"""
from django.db.models import Exists, OuterRef, Q

from apps.common.api import has_full_delivery_scope
from apps.delivery.models import DeliveryNote


def scope_orders_for(user, qs):
    """Lọc queryset `SalesOrder` theo phạm vi của `user`. Không đổi thứ tự/annotate của `qs`."""
    if has_full_delivery_scope(user):
        return qs

    assigned_q = Q(invoice__delivery_notes__assigned_to=user)
    from apps.delivery.confirmation.scope import customer_service_note_q, is_customer_service

    if is_customer_service(user):
        customer_service_q = Exists(
            DeliveryNote.objects.filter(
                sales_invoice__sales_order=OuterRef("pk")
            ).filter(customer_service_note_q(user))
        )
        return qs.filter(assigned_q | customer_service_q).distinct()

    return qs.filter(assigned_q).distinct()
