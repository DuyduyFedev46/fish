"""
Danh sách hoá đơn bán cho Kế toán (R13, 02b §3.8): lọc, phạm vi dòng, giá vốn, tổng.

Tách khỏi `api.py` để view mỏng. Chỉ ĐỌC; không đổi công thức giá vốn (nguồn là `SalesInvoiceLineBatch`, BR-BH-06).
"""
from decimal import Decimal

from django.db.models import DecimalField, Exists, F, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce

from apps.accounts.data_scopes.resolver import resolve_data_scope
from apps.common.exceptions import BusinessError
from apps.delivery.pii_scope import annotate_order_pii_visible
from apps.inventory.stock.filters import INVALID_FILTER, date_range_q, parse_choice_list_param, parse_date_param
from apps.sales.models import SalesInvoice, SalesInvoiceLineBatch, SalesOrder
from apps.sales.orders.scope import scope_orders_for

ZERO = Decimal("0")
_MONEY = DecimalField(max_digits=20, decimal_places=4)


def with_cogs(queryset):
    """Gắn `cogs` = Σ qty × unit_cost của các phân bổ lô (0 khi hoá đơn chưa có phân bổ). Subquery nên không nhân dòng."""
    per_invoice = (
        SalesInvoiceLineBatch.objects.filter(invoice_line__invoice=OuterRef("pk"))
        .order_by()
        .values("invoice_line__invoice")
        .annotate(total=Sum(F("qty") * F("unit_cost"), output_field=_MONEY))
        .values("total")
    )
    return queryset.annotate(cogs=Coalesce(Subquery(per_invoice, output_field=_MONEY), Value(ZERO), output_field=_MONEY))


def scope_invoices_for(user, queryset):
    """Phạm vi dòng (Tầng 3) theo đơn của hoá đơn: dùng chung `scope_orders_for` để không lệch với danh sách đơn.

    PV-03: giá trị lấy từ D2 (= D1 của chính nhóm có quyền xem hoá đơn, BR-PQ-37), không phụ thuộc nhóm đó có bật
    `view_orders` hay không (Q-7). `all` thì thấy hết. Còn lại chỉ thấy hoá đơn của đơn trong phạm vi, và `pii_visible`
    quyết định có hiện tên khách hay không (SR-PII-02)."""
    value = resolve_data_scope(user, "invoices")
    if value == "all":
        return queryset
    in_scope = scope_orders_for(user, SalesOrder.objects.all(), value=value).values("pk")
    visible = annotate_order_pii_visible(
        user, SalesOrder.objects.filter(pk=OuterRef("sales_order_id")), value=value)
    return queryset.filter(sales_order_id__in=in_scope).annotate(
        pii_visible=Exists(visible.filter(pii_visible=True))
    )


def filter_invoices(queryset, params):
    """`status` (nhiều), `date_from`/`date_to` (ngày VN của `issued_at`), `q` (mã hoá đơn hoặc mã đơn).

    `q` KHÔNG tìm theo tên/SĐT khách: danh sách này không phải danh bạ khách (bất biến 9)."""
    statuses = parse_choice_list_param(params, "status", SalesInvoice.Status.values)
    if statuses:
        queryset = queryset.filter(status__in=statuses)
    date_from = parse_date_param(params, "date_from")
    date_to = parse_date_param(params, "date_to")
    if date_from and date_to and date_from > date_to:
        raise BusinessError("Tham số date_from không được sau date_to.", code=INVALID_FILTER)
    queryset = queryset.filter(date_range_q(params, "issued_at"))
    term = (params.get("q") or "").strip()
    if term:
        queryset = queryset.filter(Q(code__icontains=term) | Q(sales_order__code__icontains=term))
    return queryset


def build_totals(queryset, *, with_profit):
    """Tổng trên TOÀN BỘ kết quả đã lọc (mọi trang), bỏ hoá đơn đã huỷ. `gross_profit` chỉ khi `with_profit`."""
    live = queryset.exclude(status=SalesInvoice.Status.CANCELLED).order_by()
    amount = live.aggregate(total=Coalesce(Sum("amount"), Value(ZERO), output_field=_MONEY))["total"]
    totals = {"amount": amount}
    if with_profit:
        cogs = with_cogs(live).aggregate(total=Coalesce(Sum("cogs"), Value(ZERO), output_field=_MONEY))["total"]
        totals["gross_profit"] = amount - cogs
    return totals
