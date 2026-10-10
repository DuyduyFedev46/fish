"""
S02 — Tra đơn Shop không cho dò mã đơn, không đoán SĐT (L-6, bất biến 9).
Test AC1 đến AC6. Shop lô 3+4 (SHOP-3-02): tra bằng POST mã + SĐT đầy đủ; đường GET 4 số cuối đã gỡ.
"""
import datetime
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Item, ItemGroup, ItemPrice, PriceList
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Warehouse
from apps.purchasing.models import Supplier
from apps.sales.models import Customer, SalesOrder
from apps.sales.orders import services as order_services
from apps.sales.orders.shop_api import ORDER_NOT_FOUND
from apps.sales.payments.shop_api import ORDER_NOT_FOUND as CHECKOUT_NOT_FOUND
from apps.accounts import roles


class ShopOrderLookupL6Tests(TestCase):
    def setUp(self):
        self.client = APIClient()
        g = ItemGroup.objects.create(name="Cá")
        self.item = Item.objects.create(code="CA_L6", name="Cá thu L6", item_group=g)
        pl = PriceList.objects.create(name="Bán lẻ L6", is_default=True)
        ItemPrice.objects.create(
            price_list=pl, item=self.item, rate=Decimal("100000"),
            valid_from=timezone.localdate() - datetime.timedelta(days=1),
        )
        b = batch_services.create_batch(
            item=self.item, supplier=Supplier.objects.create(name="A"),
            warehouse=Warehouse.objects.create(name="Kho"),
            received_date=timezone.localdate(),
            qty=Decimal("50"), purchase_rate=Decimal("80000"),
        )
        batch_services.publish_batch(batch=b, actor=None)

        self.order = order_services.create_order(
            customer_phone="0912345678",
            customer_name="Khách Thật",
            delivery_address="123 Đuong Bien",
            phone="0912345678",
            lines=[{"item_code": "CA_L6", "qty": Decimal("2")}],
        )
        self.valid_code = self.order.code
        self.invalid_code = "KHONGTONTAI999"

    URL = "/api/shop/orders/lookup/"

    def lookup(self, code, phone, client=None):
        return (client or self.client).post(self.URL, {"order_code": code, "phone": phone}, format="json")

    def test_s02_ac1_thieu_sdt_hoac_ma_thi_400_validation(self):
        for body in ({"order_code": self.valid_code}, {"order_code": self.valid_code, "phone": ""},
                     {"phone": "0912345678"}, {}):
            resp = self.client.post(self.URL, body, format="json")
            self.assertEqual(resp.status_code, 400, body)
            self.assertEqual(resp.json()["code"], "VALIDATION")

    def test_s02_ac2_mot_thong_diep_404_cho_moi_truong_hop_sai(self):
        resp_not_exist = self.lookup(self.invalid_code, "0900000000")
        resp_wrong_phone = self.lookup(self.valid_code, "0900000000")
        resp_four_digits = self.lookup(self.valid_code, "5678")
        for resp in (resp_not_exist, resp_wrong_phone, resp_four_digits):
            self.assertEqual(resp.status_code, 404)
            self.assertEqual(resp.json(), ORDER_NOT_FOUND)
        self.assertEqual(resp_not_exist.content, resp_wrong_phone.content)

    def test_s02_ac3_dung_thi_xem_duoc_khong_ro_pii(self):
        resp = self.lookup(self.valid_code, "0912345678")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        expected_keys = {
            "order_code", "status", "state", "status_label", "placed_at", "paid_at", "delivered_at",
            "booked_expires_at", "server_now", "hold_minutes", "payment_pending_minutes", "delivery", "lines",
            "subtotal", "discount", "total_amount", "cancel_notice", "late_payment", "lookup_token",
        }
        self.assertEqual(set(data.keys()), expected_keys)

        # Không chứa tên, SĐT, địa chỉ khách
        for forbidden in ("customer", "phone", "customer_phone", "name", "customer_name", "delivery_address", "address"):
            self.assertNotIn(forbidden, data)
        raw = resp.content.decode()
        for secret in ("0912345678", "Khách Thật", "Đuong Bien"):
            self.assertNotIn(secret, raw)

    def test_s02_ac4_sdt_co_dau_cach_hoac_cong_84(self):
        order_space = order_services.create_order(
            customer_phone="0900000678", customer_name="B", delivery_address="x",
            phone="0900 000 678", lines=[{"item_code": "CA_L6", "qty": Decimal("1")}],
        )
        self.assertEqual(self.lookup(order_space.code, "0900000678").status_code, 200)
        self.assertEqual(self.lookup(order_space.code, "+84 900 000 678").status_code, 200)

        order_plus = order_services.create_order(
            customer_phone="0900000678", customer_name="C", delivery_address="x",
            phone="+84900000678", lines=[{"item_code": "CA_L6", "qty": Decimal("1")}],
        )
        self.assertEqual(self.lookup(order_plus.code, "0900000678").status_code, 200)
        self.assertEqual(self.lookup(order_plus.code, "+84900000678").status_code, 200)

    def test_s02_ac5_checkout_ma_khong_ton_tai_tra_404_chung(self):
        resp = self.client.post(f"/api/shop/orders/{self.invalid_code}/checkout/")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json(), CHECKOUT_NOT_FOUND)
        self.assertEqual(resp.json()["code"], "ORDER_NOT_FOUND")

    def test_s02_ac6_phan_quyen_endpoint_van_cong_khai_va_user_login_tuan_thu_ac1_ac3(self):
        for role in (roles.OWNER, roles.MANAGER, roles.WAREHOUSE_STAFF, roles.DELIVERY_STAFF):
            user = make_user(f"user_{role}", role)
            client = client_for(user)
            # AC1: thiếu SĐT -> 400
            resp_bad = client.post(self.URL, {"order_code": self.valid_code}, format="json")
            self.assertEqual(resp_bad.status_code, 400)
            # AC2: sai số -> 404
            self.assertEqual(self.lookup(self.valid_code, "0900000000", client).status_code, 404)
            # AC3: đúng -> 200
            self.assertEqual(self.lookup(self.valid_code, "0912345678", client).status_code, 200)
