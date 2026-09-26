"""Mặc định hạn dùng mặt hàng (quyết định 2026-09-26: 90 -> 365 ngày)."""
from django.test import TestCase

from apps.catalog.models import Item, ItemGroup


class ItemShelfLifeDefaultTests(TestCase):
    def test_mat_hang_tao_moi_mac_dinh_han_dung_365_ngay(self):
        g = ItemGroup.objects.create(name="Cá")
        item = Item.objects.create(code="CA-DEFAULT", name="Cá mặc định", item_group=g)
        self.assertEqual(item.shelf_life_in_days, 365)
