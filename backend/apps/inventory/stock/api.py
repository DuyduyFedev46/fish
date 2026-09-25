"""
API nội bộ — kho, sổ chuyển động (chỉ đọc, append-only) và phiếu điều chỉnh kho
(người tạo = người đăng nhập, BR-PQ-16).
"""
from rest_framework import viewsets

from apps.common.api import BusinessModelPermissions, DocumentViewSet
from apps.inventory.models import StockEntry, StockLedgerEntry, Warehouse

from .serializers import StockEntrySerializer, StockLedgerEntrySerializer, WarehouseSerializer


class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [BusinessModelPermissions]


class StockEntryViewSet(DocumentViewSet):
    queryset = StockEntry.objects.select_related("batch").all()
    serializer_class = StockEntrySerializer
    permission_classes = [BusinessModelPermissions]
    actor_fields = ("created_by",)  # BR-PQ-16


class StockLedgerEntryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockLedgerEntry.objects.select_related("batch").all()
    serializer_class = StockLedgerEntrySerializer
    permission_classes = [BusinessModelPermissions]
