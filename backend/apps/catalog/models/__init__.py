"""
Danh mục & giá (P-01) — master data.

Ba dạng combo qua 2 cơ chế (decisions.md 2026-09-10 / spec 3.1):
  1. Gói có công thức  -> Item.item_type=BUNDLE + BundleLine
  2. Đóng gói sẵn      -> Item.item_type=SIMPLE thường (không cần cơ chế mới)
  3. Ưu đãi 1 tầng     -> PricingRule (không lồng nhau, không cộng dồn)

Ranh giới cố ý: KHÔNG rule engine tổng quát (BR-DM-08).

Package models/ chia theo tính năng; file này re-export để `from apps.catalog.models import X`
và Django (app_label=catalog) vẫn thấy đủ model — không sinh migration mới.
"""
from .items import KG, ItemGroup, Item, BundleLine  # noqa: F401
from .pricing import PriceList, ItemPrice, PricingRule  # noqa: F401

__all__ = [
    "KG",
    "ItemGroup",
    "Item",
    "BundleLine",
    "PriceList",
    "ItemPrice",
    "PricingRule",
]
