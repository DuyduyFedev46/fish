"""Serializer giao hàng. nv_giao chỉ sửa được trạng thái (scope ở view/queryset)."""
from rest_framework import serializers

from .models import DeliveryNote


class DeliveryNoteSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    invoice_code = serializers.CharField(source="sales_invoice.code", read_only=True)

    class Meta:
        model = DeliveryNote
        fields = [
            "id", "code", "sales_invoice", "invoice_code", "status", "status_label",
            "assigned_to", "failed_attempts", "note", "created_at", "completed_at",
        ]
        read_only_fields = [  # BR-PQ-14: chỉ `note` sửa được qua PATCH
            "code", "sales_invoice", "status", "assigned_to", "failed_attempts",
            "created_at", "completed_at",
        ]
