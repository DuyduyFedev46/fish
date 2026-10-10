"""
Shop API công khai — danh mục & bảng giá (guest, không đăng nhập). SHOP-2-01, contract 02b §3.1–3.2.

Mọi dict dựng tường minh, KHÔNG dùng serializer back-office. Không bao giờ trả số kg tồn,
giá vốn hay mã lô: chỉ trả `stock_level` ("in" | "low" | "out", BR-BH-23) — bất biến 1, BR-BH-01.
Chỉ GET (DRF trả 405 cho phương thức khác).
"""
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.images.serializers import serialize_item_image_public
from apps.catalog.models import Item
from apps.catalog.pricing.services import effective_price
from apps.sales.utils import money_str

from .services import qty_rule, sale_unit, stock_level

ITEM_NOT_FOUND = {"code": "ITEM_NOT_FOUND", "detail": "Không tìm thấy món này."}
# Lô 1–2: bốn trường chữ trả "" (lô 2b mở, có kiểm chữ BR-DM-25). Khoá luôn có mặt để FE ổn định.
DETAIL_TEXT_KEYS = ("description", "spec", "storage", "origin")


def _item_public(item, price):
    min_qty, qty_step = qty_rule(item)
    return {
        "item_code": item.code,
        "name": item.name,
        "item_type": item.item_type,
        "unit": sale_unit(item),
        "price": money_str(price),
        "stock_level": stock_level(item),
        "min_qty": money_str(min_qty),
        "qty_step": money_str(qty_step),
        "group": {"slug": item.item_group.slug, "name": item.item_group.name},
        "short_note": "",
        # A4: ảnh không phải điều kiện hiển thị (BR-DM-09) -> null khi chưa có ảnh.
        # Serializer công khai KHÔNG trả id/người tải/đường dẫn tệp gốc (bất biến 1, BR-DM-15).
        "image": serialize_item_image_public(getattr(item, "image", None)),
    }


def _group_summaries(items):
    """Chỉ nhóm có ít nhất một món trong `items`; `item_count` đếm đúng các món đó."""
    groups = {}
    for row in items:
        group = row["group"]
        entry = groups.setdefault(group["slug"], {"slug": group["slug"], "name": group["name"], "item_count": 0})
        entry["item_count"] += 1
    return sorted(groups.values(), key=lambda g: (g["name"], g["slug"]))


class ShopCatalogView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        queryset = (
            Item.objects.filter(is_active=True)
            .select_related("item_group", "image")
            .order_by("item_group__name", "code")
        )
        items = []
        for item in queryset:
            price = effective_price(item)
            if price is None:  # chỉ hiện món có giá niêm yết hiệu lực
                continue
            items.append(_item_public(item, price))
        return Response({"groups": _group_summaries(items), "items": items})


class ShopItemDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, item_code):
        item = (
            Item.objects.select_related("item_group", "image")
            .filter(code=item_code, is_active=True)
            .first()
        )
        price = effective_price(item) if item is not None else None
        if item is None or price is None:
            # Cùng một câu cho: không có mã, ngưng bán, không có giá hiệu lực (không lộ lý do nội bộ).
            return Response(ITEM_NOT_FOUND, status=404)
        data = _item_public(item, price)
        data.update({key: "" for key in DETAIL_TEXT_KEYS})
        if item.item_type == Item.ItemType.BUNDLE:
            data["bundle_components"] = [
                {
                    "item_code": line.component.code,
                    "name": line.component.name,
                    "qty_per_bundle": money_str(line.qty_per_bundle),
                    "unit": sale_unit(line.component),
                }
                for line in item.bundle_lines.select_related("component").order_by("pk")
            ]
        return Response(data)
