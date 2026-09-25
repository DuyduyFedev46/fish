"""Serializer khách hàng."""
from rest_framework import serializers

from apps.sales.models import Customer


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["id", "phone", "name", "default_address", "note", "created_at"]
        read_only_fields = ["created_at"]
