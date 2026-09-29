"""
S02 — Tra đơn Shop không cho dò mã đơn, không đoán SĐT (L-6, bất biến 9).
Test AC1 đến AC6.
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
from apps.sales.orders.shop_api import LOOKUP_BAD_LAST4, LOOKUP_NOT_FOUND


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

    def test_s02_ac1_bat_buoc_dung_4_chu_so(self):
        invalid_last4_values = ["", "8", "678", "05678", "56a8"]
        for val in invalid_last4_values:
            # Gọi với mã đơn có thật
            resp_valid = self.client.get(f"/api/shop/orders/{self.valid_code}/?phone_last4={val}")
            self.assertEqual(resp_valid.status_code, 400, f"Failed for val={val}")
            self.assertEqual(resp_valid.json(), {"detail": LOOKUP_BAD_LAST4})

            # Gọi với mã đơn không tồn tại
            resp_invalid = self.client.get(f"/api/shop/orders/{self.invalid_code}/?phone_last4={val}")
            self.assertEqual(resp_invalid.status_code, 400, f"Failed for val={val}")
            self.assertEqual(resp_invalid.json(), {"detail": LOOKUP_BAD_LAST4})

            # Response giống hệt nhau
            self.assertEqual(resp_valid.json(), resp_invalid.json())

    def test_s02_ac2_mot_thong_diep_404_cho_ca_hai_truong_hop(self):
        # Mã đơn không tồn tại + 0000
        resp_not_exist = self.client.get(f"/api/shop/orders/{self.invalid_code}/?phone_last4=0000")
        self.assertEqual(resp_not_exist.status_code, 404)
        self.assertEqual(resp_not_exist.json(), {"detail": LOOKUP_NOT_FOUND})

        # Mã đơn có thật + sai 4 số cuối (0000)
        resp_wrong_phone = self.client.get(f"/api/shop/orders/{self.valid_code}/?phone_last4=0000")
        self.assertEqual(resp_wrong_phone.status_code, 404)
        self.assertEqual(resp_wrong_phone.json(), {"detail": LOOKUP_NOT_FOUND})

        # Cùng body hoàn toàn
        self.assertEqual(resp_not_exist.json(), resp_wrong_phone.json())

    def test_s02_ac3_dung_thi_xem_duoc_khong_ro_pii(self):
        resp = self.client.get(f"/api/shop/orders/{self.valid_code}/?phone_last4=5678")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        expected_keys = {
            "order_code", "status", "status_label", "total_amount",
            "lines", "delivery", "booked_expires_at", "cancel_notice",
        }
        self.assertEqual(set(data.keys()), expected_keys)

        # Không chứa tên, SĐT, địa chỉ khách
        for forbidden in ("customer", "phone", "customer_phone", "name", "customer_name", "delivery_address", "address"):
            self.assertNotIn(forbidden, data)

    def test_s02_ac4_sdt_co_dau_cach_hoac_cong_84(self):
        order_space = order_services.create_order(
            customer_phone="0900000678", customer_name="B", delivery_address="x",
            phone="0900 000 678", lines=[{"item_code": "CA_L6", "qty": Decimal("1")}],
        )
        resp1 = self.client.get(f"/api/shop/orders/{order_space.code}/?phone_last4=0678")
        self.assertEqual(resp1.status_code, 200)

        order_plus = order_services.create_order(
            customer_phone="0900000678", customer_name="C", delivery_address="x",
            phone="+84900000678", lines=[{"item_code": "CA_L6", "qty": Decimal("1")}],
        )
        resp2 = self.client.get(f"/api/shop/orders/{order_plus.code}/?phone_last4=0678")
        self.assertEqual(resp2.status_code, 200)

    def test_s02_ac5_checkout_ma_khong_ton_tai_tra_404_chung(self):
        resp = self.client.post(f"/api/shop/orders/{self.invalid_code}/checkout/")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json(), {"detail": LOOKUP_NOT_FOUND})

    def test_s02_ac6_phan_quyen_endpoint_van_cong_khai_va_user_login_tuan_thu_ac1_ac3(self):
        for role in ("chu", "quan_ly", "nv_kho", "nv_giao"):
            user = make_user(f"user_{role}", role)
            client = client_for(user)
            # AC1: sai định dạng -> 400
            resp_bad = client.get(f"/api/shop/orders/{self.valid_code}/?phone_last4=8")
            self.assertEqual(resp_bad.status_code, 400)
            # AC2: sai số -> 404
            resp_wrong = client.get(f"/api/shop/orders/{self.valid_code}/?phone_last4=0000")
            self.assertEqual(resp_wrong.status_code, 404)
            # AC3: đúng -> 200
            resp_ok = client.get(f"/api/shop/orders/{self.valid_code}/?phone_last4=5678")
            self.assertEqual(resp_ok.status_code, 200)
