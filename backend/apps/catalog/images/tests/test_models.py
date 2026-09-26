"""Model `ItemImage` (A1 nền dữ liệu) — mỗi mặt hàng 1 ảnh (Q2), id công khai không đoán được."""
from django.db import IntegrityError
from django.test import TestCase

from apps.catalog.models import Item, ItemGroup, ItemImage


class ItemImageModelTests(TestCase):
    def setUp(self):
        g = ItemGroup.objects.create(name="Cá")
        self.item = Item.objects.create(code="CA01", name="Cá thu", item_group=g)

    def test_image_id_tu_sinh_va_khac_nhau_moi_lan(self):
        img1 = ItemImage.objects.create(item=self.item)
        self.assertTrue(img1.image_id.startswith("img_"))

        item2 = Item.objects.create(
            code="CA02", name="Cá ngừ", item_group=self.item.item_group
        )
        img2 = ItemImage.objects.create(item=item2)
        self.assertNotEqual(img1.image_id, img2.image_id)

    def test_moi_mat_hang_toi_da_1_anh_q2(self):
        ItemImage.objects.create(item=self.item)
        with self.assertRaises(IntegrityError):
            ItemImage.objects.create(item=self.item)

    def test_str_co_ma_hang_va_ma_anh(self):
        img = ItemImage.objects.create(item=self.item)
        self.assertIn(self.item.code, str(img))
        self.assertIn(img.image_id, str(img))
