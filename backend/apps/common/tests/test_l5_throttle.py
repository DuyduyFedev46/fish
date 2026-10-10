"""
S03 — Giới hạn tần suất endpoint công khai (L-5, bất biến 9).
Test AC1 đến AC6.
"""
import datetime
from decimal import Decimal
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.catalog.models import Item, ItemGroup, ItemPrice, PriceList
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Warehouse
from apps.purchasing.models import Supplier
from apps.sales.models import SalesOrder
from apps.sales.orders import services as order_services
from apps.accounts import roles


class ThrottleL5Tests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        g = ItemGroup.objects.create(name="Cá")
        self.item = Item.objects.create(code="CA_THROTTLE", name="Cá Throttle", item_group=g)
        pl = PriceList.objects.create(name="Bán lẻ", is_default=True)
        ItemPrice.objects.create(
            price_list=pl, item=self.item, rate=Decimal("100000"),
            valid_from=timezone.localdate() - datetime.timedelta(days=1),
        )
        b = batch_services.create_batch(
            item=self.item, supplier=Supplier.objects.create(name="A"),
            warehouse=Warehouse.objects.create(name="Kho"),
            received_date=timezone.localdate(),
            qty=Decimal("100"), purchase_rate=Decimal("80000"),
        )
        batch_services.publish_batch(batch=b, actor=None)

        self.order = order_services.create_order(
            customer_phone="0911223344", customer_name="Test Throttle",
            delivery_address="Kho 1", phone="0911223344",
            lines=[{"item_code": "CA_THROTTLE", "qty": Decimal("1")}],
        )

    def tearDown(self):
        cache.clear()

    @override_settings(CAVEVE_THROTTLE_RATES={"shop_lookup_ip": "5/min"})
    def test_s03_ac1_shop_lookup_ip_throttle(self):
        url = "/api/shop/orders/lookup/"
        body = {"order_code": self.order.code, "phone": "0911223344"}
        for i in range(5):
            resp = self.client.post(url, body, format="json", REMOTE_ADDR="192.168.1.100")
            self.assertEqual(resp.status_code, 200, f"Request {i+1} failed")

        resp_throttled = self.client.post(url, body, format="json", REMOTE_ADDR="192.168.1.100")
        self.assertEqual(resp_throttled.status_code, 429)
        self.assertEqual(resp_throttled.json()["code"], "throttled")
        self.assertIn("Bạn thao tác quá nhanh", resp_throttled.json()["detail"])
        self.assertIn("Retry-After", resp_throttled.headers)

    @override_settings(CAVEVE_THROTTLE_RATES={"shop_lookup_order": "3/hour"})
    def test_s03_ac1_shop_lookup_order_throttle_across_ips(self):
        url = "/api/shop/orders/lookup/"
        body = {"order_code": self.order.code, "phone": "0911223344"}
        # 3 IP khác nhau cùng tra một mã đơn
        for i in range(1, 4):
            resp = self.client.post(url, body, format="json", REMOTE_ADDR=f"10.0.0.{i}")
            self.assertEqual(resp.status_code, 200)

        # Lần 4 từ IP thứ 4 bị chặn do chạm ngưỡng mã đơn
        resp4 = self.client.post(url, body, format="json", REMOTE_ADDR="10.0.0.4")
        self.assertEqual(resp4.status_code, 429)
        self.assertEqual(resp4.json()["code"], "throttled")

    @override_settings(CAVEVE_THROTTLE_RATES={"shop_order_create": "2/hour"})
    def test_s03_ac2_shop_order_create_throttle_khong_tao_don(self):
        url = "/api/shop/orders/"
        payload = {
            "customer": {"phone": "0988776655", "name": "K"},
            "delivery_address": "X",
            "phone": "0988776655",
            "items": [{"item_code": "CA_THROTTLE", "qty": "1"}],
        }
        resp1 = self.client.post(url, payload, format="json", REMOTE_ADDR="192.168.2.1")
        self.assertEqual(resp1.status_code, 201)
        resp2 = self.client.post(url, payload, format="json", REMOTE_ADDR="192.168.2.1")
        self.assertEqual(resp2.status_code, 201)

        count_before = SalesOrder.objects.count()
        resp3 = self.client.post(url, payload, format="json", REMOTE_ADDR="192.168.2.1")
        self.assertEqual(resp3.status_code, 429)
        count_after = SalesOrder.objects.count()
        self.assertEqual(count_before, count_after, "Đơn không được tạo khi bị throttle!")

    @override_settings(CAVEVE_THROTTLE_RATES={"login_ip": "2/min", "login_user": "5/hour"})
    def test_s03_ac2_login_ip_throttle_khong_sinh_token(self):
        user = User.objects.create_user("user_throttle", password="correct_password")
        url = "/api/auth/token/"
        payload = {"username": "user_throttle", "password": "wrong_password"}

        self.client.post(url, payload, format="json", REMOTE_ADDR="192.168.3.1")
        self.client.post(url, payload, format="json", REMOTE_ADDR="192.168.3.1")

        tokens_before = Token.objects.count()
        # Request thứ 3 với mật khẩu đúng nhưng bị throttle IP
        payload_correct = {"username": "user_throttle", "password": "correct_password"}
        resp3 = self.client.post(url, payload_correct, format="json", REMOTE_ADDR="192.168.3.1")
        self.assertEqual(resp3.status_code, 429)
        tokens_after = Token.objects.count()
        self.assertEqual(tokens_before, tokens_after, "Không sinh token khi bị throttle!")

    @override_settings(CAVEVE_THROTTLE_RATES={"login_user": "2/hour"})
    def test_s03_ac2_login_user_throttle(self):
        User.objects.create_user("targeted_user", password="password123")
        url = "/api/auth/token/"
        payload = {"username": "targeted_user", "password": "wrong"}

        # 2 request từ 2 IP khác nhau
        self.client.post(url, payload, format="json", REMOTE_ADDR="172.16.0.1")
        self.client.post(url, payload, format="json", REMOTE_ADDR="172.16.0.2")

        # Request thứ 3 từ IP thứ 3 nhắm vào cùng user bị throttle
        resp3 = self.client.post(url, payload, format="json", REMOTE_ADDR="172.16.0.3")
        self.assertEqual(resp3.status_code, 429)

    @override_settings(CAVEVE_THROTTLE_RATES={
        "shop_lookup_ip": None,
        "shop_lookup_order": "",
    })
    def test_s03_ac3_tat_scope_khi_muc_la_none_hoac_rong(self):
        url = "/api/shop/orders/lookup/"
        body = {"order_code": self.order.code, "phone": "0911223344"}
        for _ in range(10):
            resp = self.client.post(url, body, format="json", REMOTE_ADDR="192.168.4.1")
            self.assertEqual(resp.status_code, 200)

    def test_s03_ac5_backoffice_khong_bi_throttle(self):
        chu = make_user("chu_backoffice", roles.OWNER)
        client = client_for(chu)
        # Gọi 50 lần liên tiếp vào endpoint backoffice
        for i in range(50):
            resp = client.get("/api/audit-logs/")
            self.assertEqual(resp.status_code, 200, f"Backoffice request {i+1} got {resp.status_code}")

    @override_settings(CAVEVE_THROTTLE_RATES={"shop_lookup_ip": "2/min"})
    def test_s03_ac6_num_proxies_dem_chung_ip_cuoi_xff(self):
        url = "/api/shop/orders/lookup/"
        body = {"order_code": self.order.code, "phone": "0911223344"}
        # Client giả mạo XFF ở đầu nhưng IP thật ở cuối là 9.9.9.9
        headers1 = {"HTTP_X_FORWARDED_FOR": "1.1.1.1, 9.9.9.9"}
        headers2 = {"HTTP_X_FORWARDED_FOR": "2.2.2.2, 9.9.9.9"}
        headers3 = {"HTTP_X_FORWARDED_FOR": "3.3.3.3, 9.9.9.9"}

        resp1 = self.client.post(url, body, format="json", **headers1)
        self.assertEqual(resp1.status_code, 200)
        resp2 = self.client.post(url, body, format="json", **headers2)
        self.assertEqual(resp2.status_code, 200)

        # Lần 3 bị throttle vì cùng IP cuối 9.9.9.9
        resp3 = self.client.post(url, body, format="json", **headers3)
        self.assertEqual(resp3.status_code, 429)
