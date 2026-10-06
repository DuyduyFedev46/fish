"""
API nội bộ — hàng giao thất bại về kho (P-08, R9). Tầng 2: approve_returntostock (BR-HV-02).

- `GET /api/inventory/returns/` (20 dòng/trang; lọc `status`, `month=YYYY-MM`) và `GET …/{id}/`.
- `POST /api/inventory/returns/` `{delivery_note, batch, qty, note?}`: tạo từ phiếu giao (xem `creation.py`).
- `POST …/{id}/approve/` `{decision: RESTOCK|WRITE_OFF}`: duyệt bằng `services.apply_return`; đã duyệt → 409 STALE_STATE.
- `POST …/{id}/cancel/` (body rỗng): huỷ phiếu còn Chờ duyệt (#8). Quyền: `approve_returntostock` / `change_returntostock`, hoặc
  người tạo phiếu (có quyền tạo) huỷ phiếu của chính mình. Phiếu đã duyệt hoặc đã huỷ → 409 STALE_STATE.
- `POST …/{id}/delete/` (body rỗng): XOÁ MỀM phiếu Chờ duyệt hoặc Đã huỷ (Duy quyết 03/10 #8). Chỉ Chủ/superuser, kiểm trước
  phạm vi dòng (người khác 403). Phiếu Đã duyệt → 400 `RETURN_DELETE_NOT_ALLOWED`; phiếu vừa bị xoá bởi request song song → 409 STALE_STATE. Trả 200 `{"status": "deleted", "id"}`; phiếu biến
  khỏi danh sách/chi tiết (404), AuditLog vẫn giữ.
- `PATCH …/{id}/`: chỉ đổi `note` khi còn Chờ duyệt. Không có HTTP DELETE (BR-PQ-10).
Phạm vi dòng: `scope.scope_returns_for` (người giao chỉ thấy phiếu của phiếu giao gán cho mình, ngoài ra 404).
Phản hồi có `Cache-Control: no-store` vì `note` là chữ tự do có thể chứa dữ liệu cá nhân (bất biến 9).
"""
from django.db import transaction
from rest_framework import status as http_status
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.staff.services import actor_is_owner
from apps.common.api import (
    BusinessModelPermissions, DocumentViewSet, NoStoreMixin, StandardPagination, reject_protected_fields, require_perm,
)
from apps.common.audit import record_audit
from apps.common.exceptions import BusinessError, ConflictError
from apps.inventory.models import ReturnToStock

from . import creation, services
from .filters import filter_list
from .scope import scope_returns_for
from .serializers import ReturnToStockSerializer

APPROVE_DECISIONS = (ReturnToStock.Decision.RESTOCK, ReturnToStock.Decision.WRITE_OFF)
# Sau khi tạo, chỉ `note` còn sửa được (và chỉ khi Chờ duyệt): số kg, lô, phiếu giao là căn cứ của kiểm tra vượt số kg.
IMMUTABLE_AFTER_CREATE = ("delivery_note", "batch", "qty", "left_warehouse_at", "returned_at")


class ReturnToStockViewSet(NoStoreMixin, DocumentViewSet):
    queryset = ReturnToStock.objects.select_related(
        "batch__item", "delivery_note__sales_invoice__sales_order",
        "created_by__staff_profile", "approved_by__staff_profile",
    ).all()
    serializer_class = ReturnToStockSerializer
    permission_classes = [BusinessModelPermissions]
    pagination_class = StandardPagination
    custom_perm_actions = ("approve", "cancel", "soft_delete")
    # BR-PQ-14: giờ rời kho / giờ về do hệ thống ghi, không nhận từ client.
    locked_fields = ("status", "decision", "approved_by", "left_warehouse_at", "returned_at")
    actor_fields = ("created_by",)  # BR-PQ-16

    def get_queryset(self):
        return scope_returns_for(self.request.user, super().get_queryset())

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if self.action == "list":
            queryset = filter_list(queryset, self.request.query_params)
        return queryset

    def perform_create(self, serializer):
        data = serializer.validated_data
        rt = creation.create_return(
            delivery_note=data["delivery_note"], batch=data["batch"], qty=data["qty"],
            actor=self.request.user, free_note=data.get("note", ""),
        )
        serializer.instance = self.get_queryset().get(pk=rt.pk)

    def update(self, request, *args, **kwargs):
        reject_protected_fields(request.data, locked=IMMUTABLE_AFTER_CREATE)
        if self.get_object().status != ReturnToStock.Status.DRAFT:
            raise BusinessError(
                "Phiếu hàng hoàn đã duyệt hoặc đã huỷ, không sửa được (BR-PQ-10).", code="RETURN_NOT_EDITABLE",
            )
        return super().update(request, *args, **kwargs)

    @staticmethod
    def _lock_or_stale(pk):
        """Khoá dòng; phiếu vừa bị request khác xoá mềm (race) → 409 STALE_STATE thay vì 500."""
        try:
            return ReturnToStock.objects.select_for_update().get(pk=pk)
        except ReturnToStock.DoesNotExist:
            raise ConflictError("Phiếu hàng hoàn đã bị xoá, hãy tải lại.", code="STALE_STATE") from None

    @action(detail=True, methods=["post"], required_perms=("inventory.approve_returntostock",))
    def approve(self, request, pk=None):
        """Duyệt phiếu hàng hoàn và nhập lại kho. Body `{"decision": "RESTOCK"|"WRITE_OFF"}` (BR-HV-02)."""
        require_perm(request.user, "inventory.approve_returntostock")
        scoped = self.get_object()  # 404 nếu ngoài phạm vi
        data = request.data if hasattr(request.data, "get") else {}
        decision = data.get("decision")
        if decision not in APPROVE_DECISIONS:
            raise BusinessError("Phải chọn Tái nhập hoặc Huỷ bỏ trước khi duyệt (BR-HV-02).", code="RETURN_DECISION_REQUIRED")
        with transaction.atomic():
            rt = self._lock_or_stale(scoped.pk)
            if rt.status != ReturnToStock.Status.DRAFT:
                raise ConflictError("Phiếu hàng hoàn đã được duyệt, hãy tải lại.", code="STALE_STATE")
            rt.decision = decision
            rt.save(update_fields=["decision"])
            services.apply_return(return_to_stock=rt, approver=request.user)  # lỗi → rollback cả `decision`
        return Response(self.get_serializer(self.get_queryset().get(pk=rt.pk)).data, status=http_status.HTTP_200_OK)

    @action(detail=True, methods=["post"], required_perms=("inventory.add_returntostock",))
    def cancel(self, request, pk=None):
        """Huỷ phiếu hàng hoàn còn Chờ duyệt (#8). Số kg của phiếu huỷ không còn tính vào số đã hoàn của phiếu giao."""
        # Cổng chung: người tạo/duyệt phiếu hàng hoàn đều có add_returntostock (chủ, quản lý, nv kho, nv giao).
        scoped = self.get_object()  # 404 nếu ngoài phạm vi
        user = request.user
        is_creator = scoped.created_by_id == user.pk and user.has_perm("inventory.add_returntostock")
        if not (
            user.has_perm("inventory.approve_returntostock") or user.has_perm("inventory.change_returntostock") or is_creator
        ):
            raise PermissionDenied("Chỉ người có quyền duyệt hoặc người tạo phiếu mới huỷ được phiếu hàng hoàn.")
        with transaction.atomic():
            rt = self._lock_or_stale(scoped.pk)
            if rt.status != ReturnToStock.Status.DRAFT:
                raise ConflictError("Phiếu hàng hoàn đã được xử lý, hãy tải lại.", code="STALE_STATE")
            rt.status = ReturnToStock.Status.CANCELLED
            rt.save(update_fields=["status"])
            record_audit(
                "cancel_returntostock", actor=user, obj=rt,
                changes={"status": {"from": ReturnToStock.Status.DRAFT, "to": ReturnToStock.Status.CANCELLED}},
            )
        return Response(self.get_serializer(self.get_queryset().get(pk=rt.pk)).data, status=http_status.HTTP_200_OK)

    @action(
        detail=True, methods=["post"], url_path="delete", url_name="delete",
        required_perms=("inventory.add_returntostock",),
    )
    def soft_delete(self, request, pk=None):
        """Xoá mềm phiếu hàng hoàn Chờ duyệt hoặc Đã huỷ (Duy quyết 03/10 #8). Chỉ Chủ hoặc superuser."""
        # Kiểm quyền Chủ TRƯỚC `get_object` để người ngoài phạm vi dòng cũng nhận 403, không lộ phiếu có tồn tại hay không.
        if not actor_is_owner(request.user):
            raise PermissionDenied("Chỉ Chủ mới xoá được phiếu hàng hoàn.")
        scoped = self.get_object()  # 404 nếu không có hoặc đã xoá
        services.delete_return(return_to_stock=scoped, actor=request.user)
        return Response({"status": "deleted", "id": scoped.pk}, status=http_status.HTTP_200_OK)
