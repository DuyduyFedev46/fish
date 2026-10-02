"""
API nội bộ — kiểm kê (P-09).

- Tạo phiếu kèm dòng số đếm: `POST /api/inventory/reconciliations/` (Tầng 1 `add_stockreconciliation`).
- Thay toàn bộ dòng: `POST …/{id}/lines/` (cần `expected_updated_at`; lệch → 409 `STALE_STATE`).
- Gửi duyệt: `POST …/{id}/submit/` (DRAFT → SUBMITTED, cần `change_stockreconciliation`); trả về nháp: `POST …/{id}/return-to-draft/`.
- Duyệt: `POST …/{id}/approve/` (Tầng 2 `approve_stockreconciliation`), chỉ phiếu SUBMITTED. Người có quyền được tự duyệt
  phiếu mình nhập (Duy chốt 02/10, #6); AuditLog ghi ai nhập, ai gửi, ai duyệt.
Không có DELETE (BR-PQ-10).
"""
from django.utils.dateparse import parse_datetime
from rest_framework import status as http_status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.audit import ai_audit_scope
from apps.common.api import BusinessModelPermissions, DocumentViewSet, StandardPagination, require_perm
from apps.common.exceptions import BusinessError
from apps.inventory.models import StockReconciliation

from . import services
from .queries import filter_list, reconciliation_queryset
from .serializers import (
    StockReconciliationDetailSerializer,
    StockReconciliationSerializer,
    parse_line_inputs,
)


def _parse_expected_updated_at(raw):
    """Thời điểm `updated_at` client đang giữ: chuỗi ISO có múi giờ. Thiếu hoặc sai → 400."""
    if raw is None:
        raise BusinessError(
            "Thiếu expected_updated_at (thời điểm cập nhật của phiếu bạn đang xem).",
            code="EXPECTED_UPDATED_AT_REQUIRED",
        )
    value = parse_datetime(raw) if isinstance(raw, str) else None
    if value is None or value.tzinfo is None:
        raise BusinessError(
            "expected_updated_at phải là thời điểm ISO có múi giờ, lấy từ updated_at của phiếu.",
            code="EXPECTED_UPDATED_AT_INVALID",
        )
    return value


class StockReconciliationViewSet(DocumentViewSet):
    queryset = StockReconciliation.objects.all()
    serializer_class = StockReconciliationSerializer
    permission_classes = [BusinessModelPermissions]
    pagination_class = StandardPagination
    custom_perm_actions = ("approve",)
    locked_fields = ("status", "approved_by", "approved_at", "updated_at")  # BR-PQ-14
    actor_fields = ("created_by",)  # BR-PQ-16: người nhập số do server gán

    def get_queryset(self):
        return reconciliation_queryset(self.request.user)

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if self.action == "list":
            queryset = filter_list(queryset, self.request.query_params)
        return queryset

    def get_serializer_class(self):
        # Danh sách gọn; chi tiết (kể cả kết quả tạo/sửa/duyệt) có `lines`.
        return StockReconciliationSerializer if self.action == "list" else StockReconciliationDetailSerializer

    def _detail(self, pk, status_code=http_status.HTTP_200_OK):
        """Đọc lại phiếu qua truy vấn có đủ cột suy ra rồi trả chi tiết."""
        obj = self.get_queryset().get(pk=pk)
        return Response(self.get_serializer(obj).data, status=status_code)

    def create(self, request, *args, **kwargs):
        """Lập phiếu kiểm kê, có thể kèm `lines` [{batch, counted_qty, reason}] (BR-KK-01)."""
        self.reject_protected_fields(request.data)
        serializer = StockReconciliationSerializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        # M1: lệnh AI chỉ có count_date, note. `lines` (nếu lọt qua) bị bỏ, dòng số đếm chỉ nhập qua …/lines/ bởi người.
        from_ai = ai_audit_scope.get() is not None
        lines = parse_line_inputs(request.data["lines"]) if "lines" in request.data and not from_ai else None
        rec = services.create_reconciliation(
            count_date=serializer.validated_data["count_date"], note=serializer.validated_data.get("note", ""),
            lines=lines, actor=request.user,
        )
        return self._detail(rec.pk, http_status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """Sửa ghi chú hoặc ngày kiểm kê của phiếu đang chờ duyệt. Dòng số đếm sửa qua `…/lines/`."""
        self.reject_protected_fields(request.data)
        if "lines" in request.data:
            raise BusinessError(
                "Dòng số đếm sửa qua POST …/lines/, không sửa qua phiếu.", code="RECON_USE_LINES_ENDPOINT",
            )
        rec = self.get_object()
        serializer = StockReconciliationSerializer(
            rec, data=request.data, partial=kwargs.get("partial", False), context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        services.update_reconciliation(
            reconciliation=rec, changes=dict(serializer.validated_data), actor=request.user
        )
        return self._detail(rec.pk)

    @action(
        detail=True, methods=["post"], url_path="lines",
        required_perms=("inventory.change_stockreconciliation",),
    )
    def replace_lines(self, request, pk=None):
        """Thay toàn bộ dòng số đếm của phiếu chờ duyệt. Body: `expected_updated_at`, `lines` [{batch, counted_qty, reason}]."""
        require_perm(request.user, "inventory.change_stockreconciliation")
        rec = self.get_object()
        data = request.data if hasattr(request.data, "get") else {}
        expected = _parse_expected_updated_at(data.get("expected_updated_at"))
        lines = parse_line_inputs(data.get("lines"))
        services.replace_lines(reconciliation=rec, lines=lines, expected_updated_at=expected, actor=request.user)
        return self._detail(rec.pk)

    @action(detail=True, methods=["post"], required_perms=("inventory.approve_stockreconciliation",))
    def approve(self, request, pk=None):
        """Duyệt phiếu kiểm kê kho và cân đối sổ kho."""
        require_perm(request.user, "inventory.approve_stockreconciliation")
        rec = services.apply_reconciliation(reconciliation=self.get_object(), approver=request.user)
        return self._detail(rec.pk)

    @action(detail=True, methods=["post"], required_perms=("inventory.change_stockreconciliation",))
    def submit(self, request, pk=None):
        """Gửi phiếu kiểm kê đi duyệt (Nháp → Chờ duyệt). Sau đó không sửa dòng được."""
        require_perm(request.user, "inventory.change_stockreconciliation")
        rec = services.submit_reconciliation(reconciliation=self.get_object(), actor=request.user)
        return self._detail(rec.pk)

    @action(
        detail=True, methods=["post"], url_path="return-to-draft",
        required_perms=("inventory.change_stockreconciliation",),
    )
    def return_to_draft(self, request, pk=None):
        """Trả phiếu chờ duyệt về nháp để sửa lại số đếm."""
        require_perm(request.user, "inventory.change_stockreconciliation")
        rec = services.return_to_draft(reconciliation=self.get_object(), actor=request.user)
        return self._detail(rec.pk)
