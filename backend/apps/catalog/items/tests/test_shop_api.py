"""Test Shop API danh mục (guest): có giá niêm yết + tồn khả dụng, KHÔNG rò giá vốn."""
import datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Item, ItemGroup, ItemPrice, PriceList
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
