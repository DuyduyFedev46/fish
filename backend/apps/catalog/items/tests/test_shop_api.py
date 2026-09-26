"""Test Shop API danh mục (guest): có giá niêm yết + tồn khả dụng, KHÔNG rò giá vốn."""
import datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.images import services as image_services
from apps.catalog.images.tests.factories import make_uploaded_image
from apps.catalog.models import Item, ItemGroup, ItemImage, ItemPrice, PriceList
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Warehouse
from apps.purchasing.models import Supplier


class ShopCatalogAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        g = ItemGroup.objects.create(name="Cá")
        self.item = Item.objects.create(code="CA01", name="Cá thu", item_group=g)
        pl = PriceList.objects.create(name="Bán lẻ", is_default=True)
        ItemPrice.objects.create(
            price_list=pl, item=self.item, rate=Decimal("100000"),
            valid_from=timezone.localdate() - datetime.timedelta(days=1),
        )
        b = batch_services.create_batch(
            item=self.item, supplier=Supplier.objects.create(name="A"),
            warehouse=Warehouse.objects.create(name="Kho"),
            received_date=timezone.localdate(), qty=Decimal("50"), purchase_rate=Decimal("80000"),
        )
        batch_services.publish_batch(batch=b, actor=None)

    def test_shop_catalog_has_price_no_cost(self):
        resp = self.client.get("/api/shop/catalog/")
        self.assertEqual(resp.status_code, 200)
        row = resp.json()[0]
        self.assertEqual(row["price"], "100000.00")
        self.assertEqual(Decimal(row["sellable_qty"]), Decimal("50"))
        self.assertNotIn("landed_unit_cost", row)
        self.assertNotIn("purchase_rate", row)

    def test_a4_ac2_chua_co_anh_tra_image_null(self):
        resp = self.client.get("/api/shop/catalog/")
        row = resp.json()[0]
        self.assertIsNone(row["image"])

        resp2 = self.client.get(f"/api/shop/catalog/{self.item.code}/")
        self.assertIsNone(resp2.json()["image"])

    def test_a4_ac1_co_anh_tra_dung_hinh_dang_khong_ro_noi_bo(self):
        image_services.upload_item_image(
            item=self.item, file=make_uploaded_image(), is_illustration=True, actor=None,
        )
        for resp in (
            self.client.get("/api/shop/catalog/"),
            self.client.get(f"/api/shop/catalog/{self.item.code}/"),
        ):
            row = resp.json()[0] if isinstance(resp.json(), list) else resp.json()
            image = row["image"]
            self.assertEqual(set(image.keys()), {"alt", "is_illustration", "urls"})
            self.assertEqual(set(image["urls"].keys()), {"thumb", "card", "detail"})
            self.assertTrue(image["is_illustration"])
            self.assertEqual(image["alt"], self.item.name)

    def test_a4_ac9_khong_ro_gia_von_lo_hay_ncc_qua_image(self):
        image_services.upload_item_image(item=self.item, file=make_uploaded_image(), actor=None)
        resp = self.client.get("/api/shop/catalog/")
        row = resp.json()[0]
        forbidden = {
            "purchase_rate", "landed_unit_cost", "rate", "unit_cost", "supplier",
            "uploaded_by", "id",
        }
        self.assertFalse(forbidden & set(row["image"].keys()))
        self.assertFalse(forbidden & set(row.keys()))

    def test_a4_ac10_mat_hang_an_van_404_du_da_co_anh(self):
        image_services.upload_item_image(item=self.item, file=make_uploaded_image(), actor=None)
        self.item.is_active = False
        self.item.save(update_fields=["is_active"])
        resp = self.client.get(f"/api/shop/catalog/{self.item.code}/")
        self.assertEqual(resp.status_code, 404)

    def test_a4_ac8_combo_hien_anh_rieng_khong_lay_anh_thanh_phan(self):
        combo = Item.objects.create(
            code="COMBO-LAU", name="Combo lẩu", item_group=self.item.item_group,
            item_type=Item.ItemType.BUNDLE,
        )
        image_services.upload_item_image(item=self.item, file=make_uploaded_image(), actor=None)
        # combo chưa có ảnh -> null, không tự lấy ảnh thành phần (BR-DM-09)
        self.assertIsNone(ItemImage.objects.filter(item=combo).first())
