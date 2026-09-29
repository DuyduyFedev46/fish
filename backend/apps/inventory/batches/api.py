"""
API nội bộ — lô hàng. Tầng 2: publish_batch, close_batch. Field trạng thái/tồn/giá vốn/hạn
khoá — chỉ đổi qua service (BR-PQ-14). Giá vốn ẩn ở serializer (Tầng 3 cột).
"""
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.ai.declare import AiMeta
from apps.common.api import BusinessModelPermissions, DocumentViewSet, require_perm
from apps.inventory.models import Batch

from . import services
from .services import FEFO_ORDER
from .serializers import BatchListQuery, BatchSerializer


class BatchViewSet(DocumentViewSet):
    # Danh sách Kho & lô theo thứ tự xuất FEFO (BR-BH-05, UC-6); Meta.ordering giữ nguyên để
    # không sinh migration.
    queryset = Batch.objects.select_related("item", "supplier", "warehouse").order_by(*FEFO_ORDER)
    serializer_class = BatchSerializer
    list_query_serializer = BatchListQuery
    ai_by_action = {"list": AiMeta(keywords=("tra_ton", "tra tồn", "tồn kho", "còn bao nhiêu kg"), sensitivity="trung_binh")}
    permission_classes = [BusinessModelPermissions]
    custom_perm_actions = ("publish", "close", "cancel_expired")
    # BR-PQ-14 / BR-GV-03: trạng thái, tồn, giá vốn, hạn chỉ đổi qua service.
    locked_fields = (
        "status", "qty_received", "qty_available", "qty_reserved", "purchase_rate",
        "landed_unit_cost", "expiry_date", "closed_at", "closed_by",
    )

    def get_queryset(self):
        qs = super().get_queryset()
        params = getattr(self.request, "query_params", None)
        if params is None:
            params = getattr(self.request, "GET", {})
        item_code = params.get("item_code")
        if item_code:
            qs = qs.filter(item__code=item_code)
        status_param = params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        return qs

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_val = self.kwargs.get(lookup_url_kwarg)
        if lookup_val and not str(lookup_val).isdigit():
            obj = get_object_or_404(self.get_queryset(), batch_id=lookup_val)
            self.check_object_permissions(self.request, obj)
            return obj
        return super().get_object()

    @action(detail=True, methods=["post"], required_perms=("inventory.publish_batch",))
    def publish(self, request, pk=None):
        """Mở bán lô cá (chuyển DRAFT sang SELLING)."""
        require_perm(request.user, "inventory.publish_batch")
        batch = services.publish_batch(batch=self.get_object(), actor=request.user)
        return Response(self.get_serializer(batch).data)

    @action(detail=True, methods=["post"], required_perms=("inventory.close_batch",), ai=AiMeta(keywords=("chot_lo", "chốt lô"), undo="defer"))
    def close(self, request, pk=None):
        """Chốt sổ lô cá sau khi bán hết hoặc quá hạn đã kiểm kê."""
        require_perm(request.user, "inventory.close_batch")
        batch = services.close_batch(batch=self.get_object(), actor=request.user)
        return Response(self.get_serializer(batch).data)

    @action(detail=True, methods=["post"], url_path="cancel-expired", required_perms=("inventory.cancel_expired_batch",))
    def cancel_expired(self, request, pk=None):
        """Huỷ lô cá quá hạn và hạch toán xuất huỷ vào sổ kho."""
        require_perm(request.user, "inventory.cancel_expired_batch")
        batch = services.cancel_expired_batch(batch=self.get_object(), actor=request.user)
        return Response(self.get_serializer(batch).data)
