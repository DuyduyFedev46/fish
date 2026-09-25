"""Serializer kho, sổ chuyển động kho, phiếu điều chỉnh kho."""
from rest_framework import serializers

from apps.inventory.models import StockEntry, StockLedgerEntry, Warehouse


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ["id", "name", "is_group"]


class StockLedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = StockLedgerEntry
        fields = ["id", "batch", "movement_type", "qty_change", "reference", "created_at"]


class StockEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = StockEntry
        fields = ["id", "purpose", "batch", "qty_change", "reason", "created_by", "created_at"]
        read_only_fields = ["created_by", "created_at"]  # BR-PQ-16
