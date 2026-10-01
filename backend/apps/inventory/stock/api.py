"""
API nội bộ — kho, sổ nhập xuất (chỉ đọc, append-only) và phiếu điều chỉnh kho.

- `GET /api/inventory/ledger/` (R6, ED-29): Sổ nhập xuất, có `balance_after`, lọc lô/loại/kho/mặt hàng/ngày.
- `GET/POST /api/inventory/warehouses/` (R7, ED-25): danh sách kho kèm số lô còn tồn; thêm kho.
- `GET /api/inventory/stock-entries/` (R7b, ED-25): danh sách phiếu điều chỉnh, ĐỌC. D-1 (Duy chốt): đợt này không
  làm form điều chỉnh tồn, FE không gọi POST; phiếu lưu một dòng và không đổi tồn.
Không có trường tiền hay giá vốn ở các endpoint này (bất biến 1): Sổ và phiếu chỉ có kg, nhãn, tên.
"""
from django.db.models import OuterRef, Q, Subquery, Sum
from django.db.models.fields import DecimalField
from rest_framework import mixins, status, viewsets
from rest_framework.response import Response

from apps.common.api import BusinessModelPermissions, DocumentViewSet, StandardPagination
from apps.inventory.models import StockEntry, StockLedgerEntry, Warehouse

from . import warehouse_services
from .filters import date_range_q, parse_choice_list_param, parse_id_param
from .references import build_lookup
from .serializers import (
    StockEntrySerializer,
    StockLedgerEntrySerializer,
    WarehouseCreateInput,
    WarehouseSerializer,
    annotate_warehouse_stock,
)


class WarehouseViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    Kho: xem (`view_warehouse`), thêm (`add_warehouse`) và đổi tên/loại (`change_warehouse`), chỉ Chủ được ghi.
    Không có DELETE: kho đã có lô bị `PROTECT` chặn, nên xoá sẽ thành lỗi 500.
    """

    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [BusinessModelPermissions]

    def get_queryset(self):
        return annotate_warehouse_stock(Warehouse.objects.all()).order_by("name", "id")

    def create(self, request, *args, **kwargs):
        payload = WarehouseCreateInput(data=request.data)
        payload.is_valid(raise_exception=True)
        warehouse = warehouse_services.create_warehouse(
            name=payload.validated_data["name"], is_group=payload.validated_data["is_group"], actor=request.user,
        )
        return Response(self.get_serializer(warehouse).data, status=status.HTTP_201_CREATED)


class StockEntryViewSet(DocumentViewSet):
    queryset = StockEntry.objects.select_related("batch__item", "created_by__staff_profile")
    serializer_class = StockEntrySerializer
    permission_classes = [BusinessModelPermissions]
    pagination_class = StandardPagination
    actor_fields = ("created_by",)  # BR-PQ-16
    # Phiếu điều chỉnh là chứng từ: không sửa, không xoá sau khi tạo (QA Lô 7 L7-B1, D-1).
    http_method_names = ["get", "post", "head", "options"]

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if self.action != "list":
            return queryset
        params = self.request.query_params
        purposes = parse_choice_list_param(params, "purpose", StockEntry.Purpose.values)
        if purposes:
            queryset = queryset.filter(purpose__in=purposes)
        return queryset.filter(date_range_q(params, "created_at"))


def _balance_after():
    """
    Tồn lô SAU dòng sổ này = tổng `qty_change` của mọi dòng cùng lô đến dòng này (xếp theo `created_at`, rồi `id`).

    Dùng truy vấn con tương quan thay cho `Window`: `Window` chạy sau `WHERE`, nên khi lọc theo loại hoặc ngày thì
    tổng lũy kế chỉ cộng các dòng còn lại và sai. Truy vấn con luôn cộng toàn bộ lịch sử của lô.
    """
    earlier = (
        StockLedgerEntry.objects.filter(batch=OuterRef("batch"))
        .filter(Q(created_at__lt=OuterRef("created_at")) | Q(created_at=OuterRef("created_at"), id__lte=OuterRef("id")))
        .order_by()
        .values("batch")
        .annotate(total=Sum("qty_change"))
        .values("total")
    )
    return Subquery(earlier, output_field=DecimalField(max_digits=14, decimal_places=3))


class StockLedgerEntryViewSet(viewsets.ReadOnlyModelViewSet):
    """Sổ nhập xuất: chỉ đọc. Mới nhất trước. Lọc: `batch`, `movement_type` (nhiều), `warehouse`, `item`, `date_from/to`."""

    queryset = StockLedgerEntry.objects.all()
    serializer_class = StockLedgerEntrySerializer
    permission_classes = [BusinessModelPermissions]
    pagination_class = StandardPagination
    reference_lookup = None

    def get_queryset(self):
        return (
            StockLedgerEntry.objects
            .select_related("batch__item", "batch__warehouse", "batch__source_line", "created_by__staff_profile")
            .annotate(balance_after=_balance_after())
            .order_by("-created_at", "-id")
        )

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if self.action != "list":
            return queryset
        params = self.request.query_params
        batch = parse_id_param(params, "batch")
        warehouse = parse_id_param(params, "warehouse")
        item = parse_id_param(params, "item")
        movement_types = parse_choice_list_param(params, "movement_type", StockLedgerEntry.MovementType.values)
        date_cond = date_range_q(params, "created_at")
        if batch:
            queryset = queryset.filter(batch_id=batch)
        if warehouse:
            queryset = queryset.filter(batch__warehouse_id=warehouse)
        if item:
            queryset = queryset.filter(batch__item_id=item)
        if movement_types:
            queryset = queryset.filter(movement_type__in=movement_types)
        return queryset.filter(date_cond)

    def paginate_queryset(self, queryset):
        page = super().paginate_queryset(queryset)
        # Tra id hoá đơn/đơn cho cả trang một lượt (không N+1).
        self.reference_lookup = build_lookup(page if page is not None else [])
        return page

    def get_object(self):
        obj = super().get_object()
        self.reference_lookup = build_lookup([obj])
        return obj

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["reference_lookup"] = self.reference_lookup
        return context
