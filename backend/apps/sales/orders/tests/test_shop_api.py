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
        self.assertNotIn("vietqr", data)  # P1-AC7: không còn QR giả
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

    def _place_order(self, phone="0912345678"):
        resp = self.client.post(
            "/api/shop/orders/",
            {
                "customer": {"phone": phone, "name": "Anh A"},
                "delivery_address": "1 Bến Cảng",
                "phone": phone,
                "items": [{"item_code": "CA01", "qty": "3"}],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        return resp.json()["order_code"]

    def test_lookup_returns_booked_expires_at_iso_vn_when_booked(self):
        """Bổ sung tra đơn Shop: BOOKED -> booked_expires_at ISO giờ VN (khớp
        SalesOrder.booked_expires_at, không suy đoán)."""
        code = self._place_order(phone="0911111111")
        order = SalesOrder.objects.get(code=code)

        resp = self.client.get(f"/api/shop/orders/{code}/?phone_last4=1111")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("booked_expires_at", data)
        expected = timezone.localtime(order.booked_expires_at).isoformat()
        self.assertEqual(data["booked_expires_at"], expected)
        # Giờ VN => offset +07:00 trong chuỗi ISO
        self.assertTrue(data["booked_expires_at"].endswith("+07:00"))

    def test_lookup_booked_expires_at_null_when_not_booked(self):
        """Bổ sung tra đơn Shop: khác BOOKED -> booked_expires_at = null (không rò TTL
        cũ của một đơn đã xong/huỷ)."""
        code = self._place_order(phone="0922222222")
        order = SalesOrder.objects.get(code=code)
        order.status = SalesOrder.Status.AUTO_CANCELLED
        order.save(update_fields=["status"])

        resp = self.client.get(f"/api/shop/orders/{code}/?phone_last4=2222")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.json()["booked_expires_at"])

    def test_lookup_returns_item_name_per_line(self):
        """Bổ sung tra đơn Shop: mỗi dòng có tên mặt hàng (`name`), khớp
        `WireOrderLine.name` FE đang đọc ở lib/api.ts (mapOrderStatus)."""
        code = self._place_order(phone="0933333333")

        resp = self.client.get(f"/api/shop/orders/{code}/?phone_last4=3333")
        self.assertEqual(resp.status_code, 200)
        lines = resp.json()["lines"]
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["item_code"], "CA01")
        self.assertEqual(lines[0]["name"], "Cá thu")

    def test_lookup_does_not_leak_internal_or_cost_fields(self):
        """Shop công khai: quét toàn bộ JSON (kể cả lồng trong `lines`) không chứa key
        giá vốn/lô/nội bộ (bất biến #1) hay SĐT/địa chỉ đầy đủ."""
        code = self._place_order(phone="0944444444")

        resp = self.client.get(f"/api/shop/orders/{code}/?phone_last4=4444")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        forbidden_keys = {
            "purchase_rate", "landed_unit_cost", "unit_cost", "rate", "batch",
            "batch_id", "cost", "profit", "phone", "customer_phone",
            "delivery_address", "address",
        }
        found_keys = set()

        def _collect(node):
            if isinstance(node, dict):
                for k, v in node.items():
                    found_keys.add(k)
                    _collect(v)
            elif isinstance(node, list):
                for item in node:
                    _collect(item)

        _collect(data)
        self.assertFalse(found_keys & forbidden_keys, found_keys & forbidden_keys)
