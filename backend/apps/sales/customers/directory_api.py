"""
API danh bạ khách cho ERP — Lô 6 / B2 (ED-13, BR-PQ-31, bất biến 9).

`GET /api/sales/customer-directory/` · `POST /api/sales/customer-directory/search/` ·
`GET|PATCH /api/sales/customer-directory/{id}/`.

- Quyền: Tầng 2 `sales.view_customer_list` (owner + manager, Chủ bật/tắt được); `PATCH` thêm `sales.change_customer`.
  Không có phạm vi dòng: quyền này = xem mọi khách. NV kho, NV giao, CSKH nhận 403 (kể cả khi có `view_customer`
  Tầng 1). NV giao vẫn xem khách của phiếu mình ở endpoint cũ `/api/sales/customers/` (không đổi).
- Số liệu (đơn, tổng mua, đơn huỷ, đơn đầu/cuối) tính bằng `annotate` Subquery trong một câu SQL, không N+1.
  `total_spent` là doanh thu của khách (không phải giá vốn) và không dính lãi lỗ.
- Không có `AiDeclarable`, và `/api/sales/customer-directory/` nằm trong `FORBIDDEN_PREFIXES` của chính sách AI.
- `POST .../search/` (Lô bổ sung A #11, Duy chốt 02/10): body `{q, ordering?, page?}`, cùng quyền, cùng shape với danh sách,
  vì từ khoá tìm (tên/SĐT khách) không được nằm trong URL/log truy cập. `GET ?q=` đã bỏ (Lô 17b-BE, TLA-L3): có `q` thì 400 `SEARCH_USE_POST`, câu lỗi không lặp lại `q`.
  `next`/`previous` trong kết quả chỉ để biết còn trang hay không; muốn sang trang khác thì gửi lại POST với `page`.
- Response gắn `Cache-Control: no-store` (chứa tên, SĐT, địa chỉ).
- `PATCH` nhận `name`, `phone`, `default_address`, `note`. `phone` chuẩn hoá bằng `normalize_phone`, trùng khách khác thì
  400 `CUSTOMER_PHONE_TAKEN` (không lặp lại số). AuditLog chỉ ghi tên trường.
"""
from decimal import Decimal

from django.db.models import Count, DateTimeField, DecimalField, F, IntegerField, Max, Min, OuterRef, Q, Subquery, Sum
from django.db.models.functions import Coalesce
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.api import BusinessModelPermissions, NoStoreMixin, SearchBodyPagination, StandardPagination
from apps.common.exceptions import BusinessError
from apps.sales.models import Customer, Refund, SalesInvoice, SalesOrder
from apps.sales.utils import fold_text

from . import services
from .permissions import CHANGE_CUSTOMER_PERM, VIEW_CUSTOMER_LIST_PERM
from .serializers import DirectoryDetailSerializer, DirectoryListSerializer, DirectoryUpdateSerializer

CANCELLED_STATUSES = (SalesOrder.Status.CANCELLED, SalesOrder.Status.AUTO_CANCELLED)
SEARCH_USE_POST = "SEARCH_USE_POST"
SEARCH_USE_POST_MESSAGE = "Tìm khách dùng ô tìm trên màn Khách hàng."
MIN_PHONE_DIGITS = 4  # tìm theo SĐT cần ít nhất 4 chữ số (không dò danh bạ bằng "0", "09")

# Khoá `ordering` được phép -> biểu thức sắp xếp. Mặc định: đơn gần nhất mới trước, khách chưa mua xếp cuối.
ORDERING = {
    "last_order_at": F("last_order_at").asc(nulls_last=True),
    "-last_order_at": F("last_order_at").desc(nulls_last=True),
    "order_count": F("order_count").asc(),
    "-order_count": F("order_count").desc(),
    "total_spent": F("total_spent").asc(),
    "-total_spent": F("total_spent").desc(),
    "name": F("name").asc(),
    "-name": F("name").desc(),
    "created_at": F("created_at").asc(),
    "-created_at": F("created_at").desc(),
}
DEFAULT_ORDERING = "-last_order_at"

MONEY = DecimalField(max_digits=16, decimal_places=2)


def _per_customer(queryset, aggregate, output_field):
    """Subquery gom một số liệu theo khách (`customer` của `queryset` trỏ tới `OuterRef('pk')`)."""
    return Subquery(
        queryset.order_by().values("customer").annotate(value=aggregate).values("value"),
        output_field=output_field,
    )


def annotate_purchase_stats(queryset):
    """Gắn `order_count`, `cancelled_count`, `first_order_at`, `last_order_at`, `total_spent`.

    `total_spent` = Σ hoá đơn ISSUED của đơn chưa huỷ − Σ khoản hoàn đã hoàn (`REFUNDED`) của chính các hoá đơn đó.
    Đơn đã trả tiền rồi huỷ bị loại cả hoá đơn lẫn khoản hoàn (không trừ hai lần). BR-HT-02/10, BR-BC-01."""
    orders = SalesOrder.objects.filter(customer=OuterRef("pk"))
    live_invoices = SalesInvoice.objects.filter(
        customer=OuterRef("pk"), status=SalesInvoice.Status.ISSUED,
    ).exclude(sales_order__status__in=CANCELLED_STATUSES)
    live_refunds = Refund.objects.filter(
        sales_invoice__customer=OuterRef("pk"),
        sales_invoice__status=SalesInvoice.Status.ISSUED,
        status=Refund.Status.REFUNDED,
    ).exclude(sales_invoice__sales_order__status__in=CANCELLED_STATUSES)
    # Refund không có `customer`: gom theo hoá đơn -> khách.
    refunds_by_customer = Subquery(
        live_refunds.order_by().values("sales_invoice__customer").annotate(value=Sum("amount")).values("value"),
        output_field=MONEY,
    )
    return queryset.annotate(
        order_count=Coalesce(_per_customer(orders, Count("pk"), IntegerField()), 0),
        cancelled_count=Coalesce(
            _per_customer(orders.filter(status__in=CANCELLED_STATUSES), Count("pk"), IntegerField()), 0,
        ),
        first_order_at=_per_customer(orders, Min("created_at"), DateTimeField()),
        last_order_at=_per_customer(orders, Max("created_at"), DateTimeField()),
        total_spent=Coalesce(_per_customer(live_invoices, Sum("amount"), MONEY), Decimal("0"), output_field=MONEY)
        - Coalesce(refunds_by_customer, Decimal("0"), output_field=MONEY),
    )


def _name_matches(query):
    """Id khách có tên chứa `query`, không dấu + không phân biệt hoa thường (như `orders.api._customer_ids_by_name`)."""
    needle = fold_text(query)
    return [pk for pk, name in Customer.objects.values_list("pk", "name") if needle in fold_text(name)]


class SearchBodySerializer(serializers.Serializer):
    q = serializers.CharField(max_length=200, allow_blank=True, required=False, default="")
    ordering = serializers.CharField(max_length=40, allow_blank=True, required=False, default="")
    page = serializers.IntegerField(min_value=1, required=False, default=1)


class CustomerDirectoryViewSet(NoStoreMixin, viewsets.GenericViewSet):
    """Danh bạ khách (list, retrieve, partial_update). Không có create/put/delete: 405."""

    queryset = Customer.objects.all()
    permission_classes = [BusinessModelPermissions]
    pagination_class = StandardPagination
    http_method_names = ["get", "post", "patch", "head", "options"]  # POST chỉ có `search/`; create vẫn 405

    @property
    def required_perms(self):
        """`BusinessModelPermissions` đọc thuộc tính này (Tầng 2): xem = một quyền, sửa = thêm `change_customer`."""
        if getattr(self, "action", None) == "partial_update":
            return (VIEW_CUSTOMER_LIST_PERM, CHANGE_CUSTOMER_PERM)
        return (VIEW_CUSTOMER_LIST_PERM,)

    def get_serializer_class(self):
        return DirectoryListSerializer if self.action == "list" else DirectoryDetailSerializer

    def get_queryset(self):
        qs = annotate_purchase_stats(Customer.objects.all())
        if self.action != "list":
            return qs
        return self.search_queryset(qs, "", self.request.query_params.get("ordering", ""))

    @staticmethod
    def search_queryset(qs, query, ordering_key):
        """Lọc theo `q` (tên không dấu hoặc SĐT ≥ 4 số) và sắp xếp; GET (không `q`) và POST `search/` dùng chung."""
        query = (query or "").strip()
        if query:
            cond = Q(pk__in=_name_matches(query))
            digits = "".join(ch for ch in query if ch.isdigit())
            if len(digits) >= MIN_PHONE_DIGITS:
                cond |= Q(phone__contains=digits)
            qs = qs.filter(cond)
        ordering = ORDERING.get(ordering_key or "", ORDERING[DEFAULT_ORDERING])
        return qs.order_by(ordering, "-id")

    def list(self, request, *args, **kwargs):
        if request.query_params.get("q", "").strip():
            # Từ khoá tên/SĐT không được nằm trong URL (bất biến 9). Không lặp lại giá trị `q`.
            raise BusinessError(SEARCH_USE_POST_MESSAGE, code=SEARCH_USE_POST)
        page = self.paginate_queryset(self.get_queryset())
        return self.get_paginated_response(self.get_serializer(page, many=True).data)

    @action(detail=False, methods=["post"], url_path="search")
    def search(self, request):
        """POST /api/sales/customer-directory/search/ — tìm khách, từ khoá nằm trong body (không vào URL/log)."""
        body = SearchBodySerializer(data=request.data if hasattr(request.data, "get") else {})
        body.is_valid(raise_exception=True)
        queryset = self.search_queryset(
            annotate_purchase_stats(Customer.objects.all()), body.validated_data["q"], body.validated_data["ordering"],
        )
        paginator = SearchBodyPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(DirectoryListSerializer(page, many=True).data)

    def retrieve(self, request, *args, **kwargs):
        return Response(self.get_serializer(self.get_object()).data)

    def partial_update(self, request, *args, **kwargs):
        customer = self.get_object()
        data = request.data
        if not hasattr(data, "keys") or not len(data):
            raise BusinessError("Không có thông tin nào để cập nhật.", code="INPUT_EMPTY")
        if set(data.keys()) - set(services.EDITABLE_PROFILE_FIELDS):
            raise BusinessError(
                "Chỉ sửa được tên, số điện thoại, địa chỉ giao mặc định và ghi chú.",
                code="INPUT_NOT_ALLOWED",
            )
        serializer = DirectoryUpdateSerializer(data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        services.update_customer_profile(
            customer=customer, changes=serializer.validated_data, actor=request.user,
        )
        return Response(self.get_serializer(self.get_queryset().get(pk=customer.pk)).data)
