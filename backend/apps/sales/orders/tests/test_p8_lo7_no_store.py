"""
P8 Lô 7 — SR-22 / No-store: API nội bộ đơn hàng và khách hàng có PII, mọi response (kể cả 401/403/404)
phải có `Cache-Control: no-store` (02b §3.3). Ma trận Group: chu, quan_ly, nv_kho, nv_giao, cskh, khách.
Dữ liệu giả.
"""
from decimal import Decimal

from django.test import TestCase

from apps.common.tests.fixtures import client_for, make_user
from apps.sales.models import Customer, SalesOrder


class NoStoreOrdersCustomersTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            phone="0900000777", name="Khách Giả A", default_address="1 Đường Giả",
        )
        self.order = SalesOrder.objects.create(
            code="SO-260930-NS01", customer=self.customer, total_amount=Decimal("100000"),
            status=SalesOrder.Status.BOOKED,
        )
        self.users = {g: make_user(f"ns_{g}", g) for g in ("chu", "quan_ly", "nv_kho", "nv_giao", "cskh")}

    def _urls(self):
        return [
            "/api/sales/orders/",
            f"/api/sales/orders/{self.order.pk}/",
            "/api/sales/customers/",
            f"/api/sales/customers/{self.customer.pk}/",
        ]

    def test_no_store_moi_nhom_tren_don_va_khach(self):
        for group, user in self.users.items():
            c = client_for(user)
            for url in self._urls():
                with self.subTest(group=group, url=url):
                    res = c.get(url)
                    self.assertIn(res.status_code, (200, 403, 404))
                    self.assertEqual(res["Cache-Control"], "no-store")

    def test_no_store_khach_chua_dang_nhap_401(self):
        c = client_for(None)
        for url in self._urls():
            with self.subTest(url=url):
                res = c.get(url)
                self.assertEqual(res.status_code, 401)
                self.assertEqual(res["Cache-Control"], "no-store")

    def test_no_store_nhom_co_quyen_thay_du_lieu_200(self):
        """Đối chứng: chu vào được (200) và vẫn no-store; không dừng ở 403 cho tất cả."""
        c = client_for(self.users["chu"])
        for url in self._urls():
            with self.subTest(url=url):
                res = c.get(url)
                self.assertEqual(res.status_code, 200, res.content)
                self.assertEqual(res["Cache-Control"], "no-store")

    def test_no_store_nv_giao_ngoai_pham_vi_404_van_no_store(self):
        res = client_for(self.users["nv_giao"]).get(f"/api/sales/customers/{self.customer.pk}/")
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res["Cache-Control"], "no-store")
