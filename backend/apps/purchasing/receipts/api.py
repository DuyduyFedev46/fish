from django.db import transaction
from django.db.models import Prefetch
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.response import Response

from apps.ai.declare import AiMeta
from apps.common.api import (
    VIEW_COSTPRICE_PERM, BusinessModelPermissions, DocumentViewSet, StandardPagination, require_perm,
)
from apps.purchasing.models import PurchaseCostAllocation, PurchaseReceipt, PurchaseReceiptLine, Supplier

from . import services, supplier_services
from .filters import filter_list
from .serializers import (
    PurchaseReceiptDetailSerializer,
    PurchaseReceiptListSerializer,
    PurchaseReceiptSerializer,
    ReceivedBatchOutput,
    ReceiveBatchesInput,
    SupplierSerializer,
)
from .supplier_queries import annotate_aggregates, attach_purchase_totals, filter_suppliers


class SupplierViewSet(viewsets.ModelViewSet):
    """
    Nhà cung cấp (B3). `GET /api/purchasing/suppliers/` (lọc `q`, `supplier_type`, `is_active`; sai → 400
    `INVALID_FILTER`) và `GET …/{id}/` kèm `receipt_count`, `last_received_at`, `purchase_total` (tiền mua, chỉ
    `view_costprice`). `POST`/`PATCH` ghi AuditLog (chỉ tên trường). "Ngừng hợp tác" = `PATCH {"is_active": false}`; DELETE và PUT trả 405.
    """

    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [BusinessModelPermissions]
    # Không xoá, không PUT (BR-PQ-10): ngừng hợp tác = PATCH is_active=false. DELETE trả 405, không ném ProtectedError.
    http_method_names = ["get", "post", "patch", "head", "options"]

    def check_permissions(self, request):
        # Method không bật → 405 cho mọi người đã đăng nhập, kể cả người thiếu quyền `delete_supplier` (như S3-AC4).
        if request.user.is_authenticated and request.method.lower() not in self.http_method_names:
            raise MethodNotAllowed(request.method)
        super().check_permissions(request)

    def get_queryset(self):
        return annotate_aggregates(super().get_queryset())

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if self.action == "list":
            queryset = filter_suppliers(queryset, self.request.query_params)
        return queryset

    def can_view_purchase_total(self):
        return self.request.user.has_perm(VIEW_COSTPRICE_PERM)

    def paginate_queryset(self, queryset):
        page = super().paginate_queryset(queryset)
        if page is not None and self.can_view_purchase_total():
            attach_purchase_totals(page)  # một truy vấn cho cả trang
        return page

    def get_object(self):
        supplier = super().get_object()
        if self.can_view_purchase_total():
            attach_purchase_totals([supplier])
        return supplier

    def _reload(self, supplier):
        """Bản có số liệu tổng hợp mới nhất để trả về sau khi ghi."""
        reloaded = self.get_queryset().get(pk=supplier.pk)
        if self.can_view_purchase_total():
            attach_purchase_totals([reloaded])
        return reloaded

    def perform_create(self, serializer):
        supplier = supplier_services.create_supplier(data=serializer.validated_data, actor=self.request.user)
        serializer.instance = self._reload(supplier)

    def perform_update(self, serializer):
        supplier = supplier_services.update_supplier(
            supplier=serializer.instance, data=serializer.validated_data, actor=self.request.user
        )
        serializer.instance = self._reload(supplier)


class PurchaseReceiptViewSet(DocumentViewSet):
    """
    Phiếu nhập (P-02). Đọc (R10): `GET /api/purchasing/receipts/` (20 dòng/trang; lọc `status`, `supplier`, `month`,
    `date_from`, `date_to`, `has_invoice`) và `GET …/{id}/` (dòng nhập, lô, hoá đơn mua, chi phí phụ). Tiền mua và giá vốn
    chỉ cho người có `view_costprice` (serializer, BR-MH-06). Ghi (tạo/sửa/ghi nhận/huỷ) giữ nguyên như trước.
    """

    queryset = PurchaseReceipt.objects.all()
    serializer_class = PurchaseReceiptSerializer
    permission_classes = [BusinessModelPermissions]
    pagination_class = StandardPagination
    custom_perm_actions = ("submit", "receive_batches", "cancel")
    locked_fields = ("status",)  # BR-PQ-14: ghi nhận qua action submit
    actor_fields = ("created_by",)  # BR-PQ-16

    def get_serializer_class(self):
        if self.action == "list":
            return PurchaseReceiptListSerializer
        if self.action == "retrieve":
            return PurchaseReceiptDetailSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action not in ("list", "retrieve"):
            return queryset.prefetch_related("lines")
        queryset = queryset.select_related("supplier", "warehouse", "created_by__staff_profile").prefetch_related(
            # order_by("id"): thứ tự dòng ổn định cho `lines[]`, `items_summary`, `batch_codes`.
            Prefetch("lines", queryset=PurchaseReceiptLine.objects.select_related("item", "batch").order_by("id")),
            "invoices",
        )
        if self.action == "retrieve" and self.request.user.has_perm(VIEW_COSTPRICE_PERM):
            # Chi phí phụ chỉ nạp khi người xem được phép thấy (giá vốn).
            queryset = queryset.prefetch_related(
                Prefetch(
                    "lines__batch__cost_allocations",
                    queryset=PurchaseCostAllocation.objects.select_related("purchase_cost"),
                )
            )
        return queryset

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if self.action == "list":
            queryset = filter_list(queryset, self.request.query_params)
        return queryset

    def perform_update(self, serializer):
        # Chỉ sửa được phiếu Nháp (BR-MH-07): kiểm trạng thái trong khoá, cùng transaction với lúc lưu.
        with transaction.atomic():
            services.lock_draft_receipt(serializer.instance)
            serializer.save()

    @action(detail=True, methods=["post"], required_perms=("purchasing.change_purchasereceipt",))
    def submit(self, request, pk=None):
        """Xác nhận phiếu nhập hàng và sinh các lô cá tương ứng."""
        # Sinh lô từ các dòng nhập (cần quyền change phiếu — Tầng 1 đã chặn).
        require_perm(request.user, "purchasing.change_purchasereceipt")
        receipt = self.get_object()
        batches = services.submit_receipt(receipt=receipt, actor=request.user)
        return Response(
            {"receipt": self.get_serializer(self.get_object()).data,
             "batches_created": [b.batch_id for b in batches]}
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="cancel",
        required_perms=("purchasing.change_purchasereceipt",),
    )
    def cancel(self, request, pk=None):
        """Huỷ phiếu nhập kho khi mọi lô còn Nháp (BR-MH-07)."""
        require_perm(request.user, "purchasing.change_purchasereceipt")
        receipt = self.get_object()
        services.cancel_receipt(receipt=receipt, actor=request.user)
        return Response({"id": receipt.id, "status": "CANCELLED"}, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["post"],
        url_path="receive-batches",
        required_perms=("purchasing.add_purchasereceipt", "purchasing.change_purchasereceipt"),
        input_serializer=ReceiveBatchesInput,
        ai=AiMeta(
            title="Nhập lô mua tại cảng",
            keywords=("nhập lô", "nhập hàng", "mua cá"),
            max_level="B",
            undo="cancel_action:cancel",
            limits={"lines[].qty": "kg", "lines[].amount": "vnd"},
        ),
    )
    def receive_batches(self, request):
        """Nhập lô mua tại cảng — mỗi dòng sinh một lô (BR-MH-01)."""
        require_perm(request.user, "purchasing.add_purchasereceipt")
        require_perm(request.user, "purchasing.change_purchasereceipt")
        serializer = ReceiveBatchesInput(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        receipt, batches = services.create_and_submit_receipt(
            **serializer.validated_data,
            actor=request.user,
        )
        receipt_data = PurchaseReceiptSerializer(receipt, context=self.get_serializer_context()).data
        batches_data = ReceivedBatchOutput(batches, many=True, context=self.get_serializer_context()).data
        return Response(
            {"receipt": receipt_data, "batches": batches_data},
            status=status.HTTP_201_CREATED,
        )
