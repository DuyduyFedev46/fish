"""
Phạm vi dòng (Tầng 3) của phiếu hoàn tiền — MỘT nguồn duy nhất, theo D1 của người gọi (C1, review Lô 3; 02b §1.5).

Phiếu hoàn có tên, SĐT khách (V2) nên là cửa phụ của danh sách đơn: nếu không lọc, Quản lý bị thu hẹp D1 vẫn thấy mọi phiếu hoàn.
Đơn của phiếu hoàn = đơn của hoá đơn (`sales_invoice`), không có thì đơn của giao dịch (`payment_transaction`).
- D1 `all` (mặc định Chủ, Quản lý, NV kho): mọi phiếu, đúng hiện trạng, kể cả phiếu chưa gắn đơn nào.
- D1 khác: chỉ phiếu của đơn trong phạm vi D1 (`scope_orders_for`); ngoài phạm vi là 404. Gắn `pii_visible` (cửa sổ SR-PII-02)
  để serializer che tên, SĐT khi phiếu giao của đơn đã kết thúc quá cửa sổ.
"""
from django.db.models import Exists, OuterRef
from django.db.models.functions import Coalesce

from apps.delivery.pii_scope import annotate_order_pii_visible
from apps.sales.models import SalesOrder
from apps.sales.orders.scope import ALL, orders_scope_value, scope_orders_for


def scope_refunds_for(user, queryset):
    value = orders_scope_value(user)
    if value == ALL:
        return queryset
    in_scope = scope_orders_for(user, SalesOrder.objects.all(), value=value).values("pk")
    visible = annotate_order_pii_visible(user, SalesOrder.objects.filter(pk=OuterRef("order_pk")), value=value)
    return queryset.annotate(
        order_pk=Coalesce("sales_invoice__sales_order_id", "payment_transaction__sales_order_id"),
    ).filter(order_pk__in=in_scope).annotate(pii_visible=Exists(visible.filter(pii_visible=True)))
