"""
API nội bộ — lô hàng. Tầng 2: publish_batch, close_batch. Field trạng thái/tồn/giá vốn/hạn
khoá — chỉ đổi qua service (BR-PQ-14). Giá vốn ẩn ở serializer (Tầng 3 cột).
"""
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.api import BusinessModelPermissions, DocumentViewSet, require_perm
from apps.inventory.models import Batch

from . import services
from .serializers import BatchSerializer


class BatchViewSet(DocumentViewSet):
    queryset = Batch.objects.select_related("item", "supplier", "warehouse").all()
    serializer_class = BatchSerializer
    permission_classes = [BusinessModelPermissions]
    custom_perm_actions = ("publish", "close")
    # BR-PQ-14 / BR-GV-03: trạng thái, tồn, giá vốn, hạn chỉ đổi qua service.
    locked_fields = (
        "status", "qty_received", "qty_available", "qty_reserved", "purchase_rate",
        "landed_unit_cost", "expiry_date", "closed_at", "closed_by",
    )

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        require_perm(request.user, "inventory.publish_batch")
        batch = services.publish_batch(batch=self.get_object(), actor=request.user)
        return Response(self.get_serializer(batch).data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        require_perm(request.user, "inventory.close_batch")
        batch = services.close_batch(batch=self.get_object(), actor=request.user)
        return Response(self.get_serializer(batch).data)
