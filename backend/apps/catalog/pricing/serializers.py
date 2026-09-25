"""Serializer bảng giá, giá niêm yết, ưu đãi (không có field giá vốn)."""
from rest_framework import serializers

from apps.catalog.models import ItemPrice, PriceList, PricingRule


class PriceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceList
        fields = ["id", "name", "currency", "is_default"]


class ItemPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemPrice
        fields = ["id", "price_list", "item", "rate", "valid_from", "valid_upto"]


class PricingRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PricingRule
        fields = [
            "id", "name", "is_active", "apply_on", "item", "min_qty", "min_amount",
            "discount_type", "discount_value", "valid_from", "valid_upto",
        ]
