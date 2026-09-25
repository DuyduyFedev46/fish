"""Test Shop API đặt hàng & tra đơn (guest)."""
import datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Item, ItemGroup, ItemPrice, PriceList
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Warehouse
from apps.purchasing.models import Supplier
from apps.sales.models import SalesOrder


class ShopOrderAPITests(TestCase):
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

    def test_shop_order_create_and_lookup(self):
        resp = self.client.post(
            "/api/shop/orders/",
            {
                "customer": {"phone": "0912345678", "name": "Anh A"},
                "delivery_address": "1 Bến Cảng",
                "phone": "0912345678",
                "items": [{"item_code": "CA01", "qty": "3"}],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        data = resp.json()
        self.assertEqual(data["total_amount"], "300000.00")
        self.assertEqual(data["vietqr"]["content"], data["order_code"])
        code = data["order_code"]

        # tra đúng 4 số cuối
        ok = self.client.get(f"/api/shop/orders/{code}/?phone_last4=5678")
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.json()["status"], SalesOrder.Status.BOOKED)
        # sai 4 số cuối -> 404
        bad = self.client.get(f"/api/shop/orders/{code}/?phone_last4=0000")
        self.assertEqual(bad.status_code, 404)

    def test_shop_order_insufficient_stock_returns_400(self):
        resp = self.client.post(
            "/api/shop/orders/",
            {
                "customer": {"phone": "0912000000"},
                "delivery_address": "x", "phone": "0912000000",
                "items": [{"item_code": "CA01", "qty": "999"}],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
