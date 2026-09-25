"""API nội bộ — bảng giá, giá niêm yết theo hiệu lực, ưu đãi 1 tầng (P-01). CRUD theo perm model."""
from rest_framework import viewsets

from apps.catalog.models import ItemPrice, PriceList, PricingRule
from apps.common.api import BusinessModelPermissions

from .serializers import ItemPriceSerializer, PriceListSerializer, PricingRuleSerializer


class PriceListViewSet(viewsets.ModelViewSet):
    queryset = PriceList.objects.all()
    serializer_class = PriceListSerializer
    permission_classes = [BusinessModelPermissions]


class ItemPriceViewSet(viewsets.ModelViewSet):
    queryset = ItemPrice.objects.select_related("item", "price_list").all()
    serializer_class = ItemPriceSerializer
    permission_classes = [BusinessModelPermissions]


class PricingRuleViewSet(viewsets.ModelViewSet):
    queryset = PricingRule.objects.all()
    serializer_class = PricingRuleSerializer
    permission_classes = [BusinessModelPermissions]
