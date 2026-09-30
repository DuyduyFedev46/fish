"""
Rà soát A2 (2026-09-30-ra-soat-agy) — S03-AC2 (L-5, bất biến 9,
doc/features/2026-09-28-sua-loi-bao-mat/02-stories.md).

`apps/common/tests/test_l5_throttle.py` đã kiểm scope `shop_lookup_ip`, `shop_lookup_order`,
`shop_order_create`, `login_ip`, `login_user` — nhưng CHƯA có ca nào gọi thật
`POST /api/shop/orders/<mã>/checkout/` (`ShopCheckoutThrottle`, scope `shop_checkout`) dù
S03-AC2 yêu cầu rõ "Tương tự AC1 cho ... POST /api/shop/orders/<mã>/checkout/ (shop_checkout)".
File này lấp khoảng trống bằng chứng đó — không sửa code sản phẩm.
"""
import datetime
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Item, ItemGroup, ItemPrice, PriceList
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Warehouse
from apps.purchasing.models import Supplier
from apps.sales.models import SalesOrder
from apps.sales.orders import services as order_services


class ShopCheckoutThrottleTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        g = ItemGroup.objects.create(name="Cá")
        item = Item.objects.create(code="CA_CKT", name="Cá checkout throttle", item_group=g)
        pl = PriceList.objects.create(name="Bán lẻ CKT", is_default=True)
        ItemPrice.objects.create(
            price_list=pl, item=item, rate=Decimal("100000"),
            valid_from=timezone.localdate() - datetime.timedelta(days=1),
        )
        b = batch_services.create_batch(
            item=item, supplier=Supplier.objects.create(name="A"),
            warehouse=Warehouse.objects.create(name="Kho"),
            received_date=timezone.localdate(),
            qty=Decimal("100"), purchase_rate=Decimal("80000"),
        )
        batch_services.publish_batch(batch=b, actor=None)
        self.order = order_services.create_order(
            customer_phone="0900001111", customer_name="Khách checkout throttle",
            delivery_address="Kho 1", phone="0900001111",
            lines=[{"item_code": "CA_CKT", "qty": Decimal("1")}],
        )

    def tearDown(self):
        cache.clear()

    @override_settings(
        CAVEVE_THROTTLE_RATES={"shop_checkout": "2/min"},
        SEPAY_MERCHANT_ID="TEST-MERCHANT",
    )
    def test_s03_ac2_shop_checkout_throttle_khong_tang_checkout_attempts(self):
        url = f"/api/shop/orders/{self.order.code}/checkout/"
        resp1 = self.client.post(url, REMOTE_ADDR="192.168.9.1")
        self.assertEqual(resp1.status_code, 200, resp1.content)
        resp2 = self.client.post(url, REMOTE_ADDR="192.168.9.1")
        self.assertEqual(resp2.status_code, 200, resp2.content)

        attempts_before = SalesOrder.objects.get(pk=self.order.pk).checkout_attempts
        resp3 = self.client.post(url, REMOTE_ADDR="192.168.9.1")
        self.assertEqual(resp3.status_code, 429)
        self.assertEqual(resp3.json()["code"], "throttled")
        self.assertIn("Retry-After", resp3.headers)

        attempts_after = SalesOrder.objects.get(pk=self.order.pk).checkout_attempts
        self.assertEqual(
            attempts_before, attempts_after,
            "Request bị throttle không được tính thêm lần thử thanh toán (không đổi trạng thái đơn).",
        )

    @override_settings(CAVEVE_THROTTLE_RATES={"shop_checkout": "1/min"})
    def test_s03_ac2_shop_checkout_throttle_ca_khi_ma_don_khong_ton_tai(self):
        # Ngoài đường thuận: throttle phải áp dụng cả khi mã đơn không tồn tại, để không
        # thể dùng checkout như một kênh dò mã đơn khác né được S02.
        url = "/api/shop/orders/KHONGTONTAICKT/checkout/"
        resp1 = self.client.post(url, REMOTE_ADDR="192.168.9.2")
        self.assertEqual(resp1.status_code, 404)
        resp2 = self.client.post(url, REMOTE_ADDR="192.168.9.2")
        self.assertEqual(resp2.status_code, 429)
