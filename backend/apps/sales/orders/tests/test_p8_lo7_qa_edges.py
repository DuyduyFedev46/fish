"""
QA P8 Lô 7 — no-store: phủ mọi động từ (POST/PATCH/DELETE/OPTIONS), action tuỳ biến, id không tồn tại, tìm theo SĐT.
Đồng thời quét (chỉ ghi nhận) các API nội bộ khác có dữ liệu khách xem có no-store chưa. Dữ liệu giả.
"""
from decimal import Decimal

from django.test import TestCase

from apps.common.tests.fixtures import client_for, make_user
from apps.sales.models import Customer, SalesOrder
from apps.accounts import roles


class QaNoStoreVerbs(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(phone="0900000888", name="Khách Giả C", default_address="3 Đường Giả")
        self.order = SalesOrder.objects.create(
            code="SO-260930-QA01", customer=self.customer, total_amount=Decimal("100000"),
            status=SalesOrder.Status.BOOKED,
        )
        self.users = {g: make_user(f"qns_{g}", g) for g in (roles.OWNER, roles.MANAGER, roles.WAREHOUSE_STAFF, roles.DELIVERY_STAFF, roles.CUSTOMER_SERVICE)}

    def test_moi_dong_tu_moi_nhom_deu_no_store(self):
        cases = [
            ("get", "/api/sales/orders/?search=0900000888", None),
            ("get", "/api/sales/orders/?search=Kh%C3%A1ch", None),
            ("get", "/api/sales/orders/99999999/", None),
            ("get", "/api/sales/customers/?search=0900000888", None),
            ("get", "/api/sales/customers/99999999/", None),
            ("options", "/api/sales/orders/", None),
            ("options", "/api/sales/customers/", None),
            ("post", f"/api/sales/orders/{self.order.pk}/cancel/", {"reason": "thử"}),
            ("post", f"/api/sales/orders/{self.order.pk}/confirm-payment/", {}),
            ("post", "/api/sales/orders/", {}),
            ("post", "/api/sales/customers/", {"phone": "0900000001", "name": "X"}),
            ("patch", f"/api/sales/customers/{self.customer.pk}/", {"name": "Y"}),
        ]
        seen = set()
        for group, user in self.users.items():
            c = client_for(user)
            for method, url, body in cases:
                with self.subTest(group=group, method=method, url=url):
                    res = getattr(c, method)(url, body, format="json") if body is not None else getattr(c, method)(url)
                    seen.add(res.status_code)
                    self.assertEqual(res["Cache-Control"], "no-store", f"{res.status_code} {res.content[:120]}")
        self.assertTrue({200, 403} <= seen, seen)

    def test_xoa_khach_da_co_don_khong_mat_du_lieu_chung_tu(self):
        """Bất biến: không xoá chứng từ. Khách đã có đơn: DB chặn (ProtectedError). Ghi nhận mã trả về."""
        c = client_for(self.users[roles.OWNER])
        c.raise_request_exception = False
        res = c.delete(f"/api/sales/customers/{self.customer.pk}/")
        print("QA-INFO DELETE khach co don ->", res.status_code)
        self.assertNotIn(res.status_code, (200, 204))
        self.assertTrue(Customer.objects.filter(pk=self.customer.pk).exists())
        self.assertTrue(SalesOrder.objects.filter(pk=self.order.pk).exists())

    def test_khach_chua_dang_nhap_moi_dong_tu_401_no_store(self):
        c = client_for(None)
        for method, url in (("get", "/api/sales/orders/"), ("post", "/api/sales/customers/"),
                            ("patch", f"/api/sales/customers/{self.customer.pk}/"),
                            ("post", f"/api/sales/orders/{self.order.pk}/cancel/")):
            with self.subTest(method=method, url=url):
                res = getattr(c, method)(url)
                self.assertEqual(res.status_code, 401)
                self.assertEqual(res["Cache-Control"], "no-store")

    def test_ghi_nhan_api_noi_bo_khac_co_du_lieu_khach_da_co_no_store_chua(self):
        """Không fail: chỉ liệt kê để báo cáo. In ra các URL 200 thiếu no-store."""
        chu = client_for(self.users[roles.OWNER])
        urls = ["/api/delivery/notes/", "/api/delivery/cskh/queue/", "/api/payments/", "/api/sales/payments/",
                "/api/refunds/", "/api/sales/refunds/", "/api/invoices/", "/api/sales/invoices/"]
        missing = []
        for u in urls:
            r = chu.get(u)
            if r.status_code == 200 and r.get("Cache-Control") != "no-store":
                missing.append(u)
        print("QA-INFO thiếu no-store (200):", missing)
