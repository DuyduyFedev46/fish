"""
Shop API công khai — danh mục & bảng giá (guest, không đăng nhập).
KHÔNG lộ giá vốn: chỉ trả giá niêm yết + tồn khả dụng (BR-BH-01/DM-06).
"""
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Item
from apps.catalog.pricing.services import effective_price

from .services import sellable_qty


def _item_public(item):
    # Tiền & kg trả dạng chuỗi cho nhất quán với DRF serializer (tránh float mất chính xác).
    price = effective_price(item)
    return {
        "item_code": item.code,
        "name": item.name,
        "group": item.item_group.name,
        "item_type": item.item_type,
        "unit": "Kg",
        "price": str(price) if price is not None else None,
        "sellable_qty": str(sellable_qty(item)),
    }


class ShopCatalogView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        items = (
            Item.objects.filter(is_active=True)
            .select_related("item_group")
            .order_by("item_group__name", "code")
        )
        # Chỉ hiển thị mặt hàng đã có giá niêm yết hiệu lực.
        data = [d for d in (_item_public(it) for it in items) if d["price"] is not None]
        return Response(data)


class ShopItemDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, item_code):
        try:
            item = Item.objects.select_related("item_group").get(code=item_code, is_active=True)
        except Item.DoesNotExist:
            return Response({"detail": "Không tìm thấy mặt hàng."}, status=404)
        data = _item_public(item)
        if item.item_type == Item.ItemType.BUNDLE:
            data["bundle_components"] = [
                {
                    "item_code": bl.component.code,
                    "name": bl.component.name,
                    "qty_per_bundle": str(bl.qty_per_bundle),
                }
                for bl in item.bundle_lines.select_related("component")
            ]
        return Response(data)
